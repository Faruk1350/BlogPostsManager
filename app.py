import logging
import os

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from prometheus_client import Counter, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- LOGGING ----------------
LOG_FILE = os.getenv("LOG_FILE")

log_handlers = [logging.StreamHandler()]
if LOG_FILE:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_handlers.append(logging.FileHandler(LOG_FILE))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger("blog")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "blog-posts-manager-secret-key")

# ---------------- METRICS ----------------
# Exposes /metrics: per-endpoint request totals, durations, exceptions
# plus the default process/GC collectors.
metrics = PrometheusMetrics(app)
metrics.info(
    "blog_app_info",
    "Blog Posts Manager application info",
    version=os.getenv("APP_VERSION", "dev"),
)

posts_created_total = Counter("blog_posts_created_total", "Total blog posts created")
signups_total = Counter("blog_signups_total", "Total user signups")
logins_total = Counter("blog_logins_total", "Total successful logins")
login_failures_total = Counter("blog_login_failures_total", "Total failed login attempts")
posts_gauge = Gauge("blog_posts_count", "Current number of blog posts")

# ---------------- USERS ----------------
users = []

# ---------------- POSTS ----------------
posts = [
    {
        "id": 1,
        "title": "My First Blog",
        "content": "Welcome to Blog Posts Manager!",
        "author": "Admin"
    }
]

posts_gauge.set(len(posts))


# ---------------- HOME / DASHBOARD ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        posts=posts,
        user=session["user"]
    )


# ---------------- SIGN UP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Check existing email
        for user in users:
            if user["email"] == email:
                logger.warning("SIGNUP REJECTED email=%s reason=already_registered", email)
                return "Email already registered!"

        new_user = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        }

        users.append(new_user)
        signups_total.inc()
        logger.info("SIGNUP email=%s name=%s", email, name)

        return redirect(url_for("login"))

    return render_template("signup.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        for user in users:
            if user["email"] == email and check_password_hash(
                user["password"], password
            ):
                session["user"] = user["name"]
                session["email"] = user["email"]

                logins_total.inc()
                logger.info("LOGIN OK email=%s ip=%s", email, request.remote_addr)

                return redirect(url_for("home"))

        login_failures_total.inc()
        logger.warning("LOGIN FAILED email=%s ip=%s", email, request.remote_addr)
        return "Invalid email or password!"

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- GET POSTS API ----------------
@app.route("/items", methods=["GET"])
def get_items():
    return jsonify(posts)


# ---------------- ADD POST API ----------------
@app.route("/items", methods=["POST"])
def add_item():

    if "user" not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.get_json()

    new_post = {
        "id": len(posts) + 1,
        "title": data["title"],
        "content": data["content"],
        "author": session["user"]
    }

    posts.append(new_post)
    posts_created_total.inc()
    posts_gauge.set(len(posts))
    logger.info(
        "POST CREATED id=%s title=%s author=%s", new_post["id"], new_post["title"], new_post["author"]
    )

    return jsonify(new_post), 201


# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))