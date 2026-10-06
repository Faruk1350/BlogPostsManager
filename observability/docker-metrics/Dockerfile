FROM python:3.12-slim

RUN pip install --no-cache-dir "docker>=7,<8" "prometheus-client>=0.20"

COPY exporter.py /exporter.py

EXPOSE 9417

CMD ["python", "/exporter.py"]
