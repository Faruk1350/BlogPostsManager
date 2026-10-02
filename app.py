from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "blog-posts-manager-secret-key"

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
                return "Email already registered!"

        new_user = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        }

        users.append(new_user)

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

                return redirect(url_for("home"))

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

    return jsonify(new_post), 201


# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)