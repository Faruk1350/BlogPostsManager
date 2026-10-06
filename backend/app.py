from flask import Flask
from flask_cors import CORS

from backend.routes.items import items_bp
from backend.routes.health import health_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(items_bp)
app.register_blueprint(health_bp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)