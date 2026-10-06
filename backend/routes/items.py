from flask import Blueprint, jsonify, request
from backend.supabase_client import supabase

items_bp = Blueprint("items", __name__)


@items_bp.route("/items", methods=["GET"])
def get_items():
    response = supabase.table("posts").select("*").order("id").execute()
    return jsonify(response.data)


@items_bp.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()

    if not data or not data.get("title") or not data.get("content"):
        return jsonify({"error": "Title and content are required"}), 400

    new_post = {
        "title": data["title"],
        "content": data["content"],
        "author": data.get("author", "Admin")
    }

    response = supabase.table("posts").insert(new_post).execute()

    return jsonify(response.data[0]), 201