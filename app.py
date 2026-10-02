from flask import Flask, request, jsonify

app = Flask(__name__)

posts = [
    {
        "id": 1,
        "title": "My First Blog",
        "content": "Welcome to Blog Posts Manager!"
    }
]


@app.route("/items", methods=["GET"])
def get_items():
    return jsonify(posts)


@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()

    new_post = {
        "id": len(posts) + 1,
        "title": data["title"],
        "content": data["content"]
    }

    posts.append(new_post)
    return jsonify(new_post), 201


@app.route("/health", methods=["GET"])
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)