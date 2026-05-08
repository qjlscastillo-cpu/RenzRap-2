from flask import Blueprint, request, jsonify, session, render_template
from db import get_connection, hash_password
import mysql.connector

users_bp = Blueprint("users", __name__)

@users_bp.route("/profile")
def profile():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("profile.html")

@users_bp.route("/api/users", methods=["GET"])
def get_users():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id, name, username, role FROM users")
    users = cur.fetchall()
    cur.close()
    con.close()
    return jsonify(users)

@users_bp.route("/api/users", methods=["POST"])
def add_user():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    name     = data.get("name", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "").strip()
    if not all([name, username, password, role]):
        return jsonify({"success": False, "message": "All fields are required."}), 400
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users (name, username, password, role) VALUES (%s, %s, %s, %s)",
            (name, username, hash_password(password), role)
        )
        con.commit()
        cur.close()
        con.close()
        return jsonify({"success": True})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists."}), 409

@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def edit_user(user_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    name     = data.get("name", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role     = data.get("role", "").strip()
    con = get_connection()
    cur = con.cursor()
    if password:
        cur.execute(
            "UPDATE users SET name=%s, username=%s, password=%s, role=%s WHERE id=%s",
            (name, username, hash_password(password), role, user_id)
        )
    else:
        cur.execute(
            "UPDATE users SET name=%s, username=%s, role=%s WHERE id=%s",
            (name, username, role, user_id)
        )
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})

@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})