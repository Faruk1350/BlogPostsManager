"""Prometheus exporter for Docker container metrics.

cAdvisor does not work on macOS container runtimes (OrbStack/Docker Desktop),
so this exporter reads container stats directly from the Docker API socket and
exposes the same signals we need: CPU, memory, network, block IO, restarts and
running state per container.
"""

import os
import socketserver
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from docker import DockerClient
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

INTERVAL = float(os.getenv("SCRAPE_INTERVAL", "15"))
DOCKER_HOST = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
# Only containers whose name starts with this prefix are exported. Set to an
# empty string to export every container on the daemon (slower collection).
SCOPE_PREFIX = os.getenv("EXPORTER_CONTAINER_PREFIX", "blog-")

client = DockerClient(base_url=DOCKER_HOST)

exporter_up = Gauge("docker_exporter_up", "1 when the Docker API is reachable")

LABELS = ["name", "image"]
container_running = Gauge("docker_container_running", "1 when the container is running", LABELS)
container_restarts = Gauge("docker_container_restarts", "Number of times the container restarted", LABELS)
container_start_time = Gauge("docker_container_start_time_seconds", "Container start time (unix seconds)", LABELS)
container_cpu = Gauge("docker_container_cpu_percent", "CPU usage, percent of one core", LABELS)
container_mem = Gauge("docker_container_memory_bytes", "Memory usage bytes", LABELS)
container_mem_limit = Gauge("docker_container_memory_limit_bytes", "Memory limit bytes", LABELS)
container_mem_pct = Gauge("docker_container_memory_percent", "Memory usage, percent of limit", LABELS)
container_net_rx = Gauge("docker_container_network_receive_bytes", "Cumulative received bytes", LABELS)
container_net_tx = Gauge("docker_container_network_transmit_bytes", "Cumulative transmitted bytes", LABELS)
container_blk_read = Gauge("docker_container_block_read_bytes", "Cumulative block read bytes", LABELS)
container_blk_write = Gauge("docker_container_block_write_bytes", "Cumulative block write bytes", LABELS)

_previous = set()


def _started_seconds(value):
    try:
        return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except (TypeError, ValueError):
        return 0


def _cpu_percent(stats):
    cpu = stats.get("cpu_stats", {})
    pre = stats.get("precpu_stats", {})
    cpu_delta = cpu.get("cpu_usage", {}).get("total_usage", 0) - pre.get("cpu_usage", {}).get("total_usage", 0)
    system_delta = cpu.get("system_cpu_usage", 0) - pre.get("system_cpu_usage", 0)
    online = cpu.get("online_cpus") or len(cpu.get("cpu_usage", {}).get("percpu_usage") or []) or 1
    if system_delta <= 0 or cpu_delta < 0:
        return 0.0
    return round(cpu_delta / system_delta * online * 100, 2)


def _io_bytes(stats, op):
    entries = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
    return sum(e.get("value", 0) for e in entries if e.get("op") == op)


def _collect_container(container):
    """Update all gauges for a single container. Runs in a worker thread."""
    name = container.name
    image = (container.image.tags or ["<none>"])[0]
    labels = dict(name=name, image=image)

    container_restarts.labels(**labels).set(container.attrs.get("RestartCount", 0))
    running = container.status == "running"
    container_running.labels(**labels).set(1 if running else 0)

    if not running:
        container_cpu.labels(**labels).set(0)
        return name, image

    container_start_time.labels(**labels).set(_started_seconds(container.attrs.get("State", {}).get("StartedAt")))
    try:
        stats = container.stats(stream=False)
    except Exception:  # container vanished between list and stats
        return name, image

    container_cpu.labels(**labels).set(_cpu_percent(stats))

    memory = stats.get("memory_stats", {})
    usage = memory.get("usage", 0)
    limit = memory.get("limit", 0)
    container_mem.labels(**labels).set(usage)
    container_mem_limit.labels(**labels).set(limit)
    container_mem_pct.labels(**labels).set(round(usage / limit * 100, 2) if limit else 0)

    networks = stats.get("networks") or {}
    container_net_rx.labels(**labels).set(sum(n.get("rx_bytes", 0) for n in networks.values()))
    container_net_tx.labels(**labels).set(sum(n.get("tx_bytes", 0) for n in networks.values()))

    container_blk_read.labels(**labels).set(_io_bytes(stats, "Read"))
    container_blk_write.labels(**labels).set(_io_bytes(stats, "Write"))

    return name, image


def collect():
    """One collection pass. Returns the set of (name, image) seen."""
    containers = client.containers.list(all=True)
    if SCOPE_PREFIX:
        containers = [container for container in containers if container.name.startswith(SCOPE_PREFIX)]
    with ThreadPoolExecutor(max_workers=16) as pool:
        return set(pool.map(_collect_container, containers))


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") not in ("/metrics", ""):
            self.send_error(404)
            return
        body = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence access logging
        return


class MetricsServer(ThreadingHTTPServer):
    """HTTPServer without the slow/hanging socket.getfqdn() reverse lookup."""

    allow_reuse_address = True

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


if __name__ == "__main__":
    server = MetricsServer(("127.0.0.1", 9417), MetricsHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"docker-metrics exporter on 127.0.0.1:9417 (interval {INTERVAL}s, scope '{SCOPE_PREFIX or 'all'}')", flush=True)

    previous = set()
    while True:
        started = time.monotonic()
        try:
            seen = collect()
            exporter_up.set(1)
        except Exception as exc:
            exporter_up.set(0)
            print(f"collect failed: {exc}", flush=True)
            time.sleep(INTERVAL)
            continue

        # Drop series for containers that no longer exist.
        for name, image in previous - seen:
            for gauge in (
                container_running,
                container_restarts,
                container_start_time,
                container_cpu,
                container_mem,
                container_mem_limit,
                container_mem_pct,
                container_net_rx,
                container_net_tx,
                container_blk_read,
                container_blk_write,
            ):
                gauge.remove(name, image)
        previous = seen

        elapsed = time.monotonic() - started
        time.sleep(max(1.0, INTERVAL - elapsed))
