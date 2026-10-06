from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# In-memory list to store blog posts
posts = []


@app.route("/items", methods=["GET"])
def get_posts():
    return jsonify(posts)


@app.route("/items", methods=["POST"])
def add_post():
    data = request.get_json()

    post = {
        "id": len(posts) + 1,
        "title": data["title"],
        "content": data["content"],
        "author": data["author"]
    }

    posts.append(post)

    return jsonify(post), 201


@app.route("/health", methods=["GET"])
def health_check():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)