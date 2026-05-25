from flask import Blueprint, request, jsonify, session, render_template, redirect
from db import get_connection, hash_password
from routes.logger import log_action
import mysql.connector

users_bp = Blueprint("users", __name__)

@users_bp.route("/profile")
def profile():
    if not session.get("logged_in"):
        return redirect("/")
    if session.get("role", "").lower() != "admin":
        return redirect("/dashboard")
    return render_template("profile.html", active_page="profile", role=session.get("role"))

@users_bp.route("/api/users", methods=["GET"])
def get_users():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id, name, username, role, inactive, email, phone, address, date_hired FROM users")
    users = cur.fetchall()
    cur.close()
    con.close()
    return jsonify(users)

@users_bp.route("/api/users", methods=["POST"])
def add_user():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    name      = data.get("name", "").strip()
    username  = data.get("username", "").strip()
    password  = data.get("password", "").strip()
    role      = data.get("role", "").strip()
    inactive  = data.get("inactive", False)
    email     = data.get("email", "").strip()
    phone     = data.get("phone", "").strip()
    address   = data.get("address", "").strip()
    date_hired = data.get("date_hired", "")
    if not all([name, username, password, role]):
        return jsonify({"success": False, "message": "All fields are required."}), 400
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users (name, username, password, role, inactive, email, phone, address, date_hired) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (name, username, hash_password(password), role, inactive, email, phone, address, date_hired or None)
        )
        con.commit()
        cur.close()
        con.close()
        log_action(f"Added user: {name} | Username: {username} | Role: {role}")
        return jsonify({"success": True})
    except mysql.connector.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists."}), 409

@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def edit_user(user_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    name      = data.get("name", "").strip()
    username  = data.get("username", "").strip()
    password  = data.get("password", "").strip()
    role      = data.get("role", "").strip()
    inactive  = data.get("inactive")
    email     = data.get("email", "").strip()
    phone     = data.get("phone", "").strip()
    address   = data.get("address", "").strip()
    date_hired = data.get("date_hired", "")

    con = get_connection()

    # ── Fetch old values BEFORE updating ──
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT name, username, role, inactive, email, phone, address, date_hired FROM users WHERE id=%s", (user_id,))
    old = cur.fetchone()

    cur2 = con.cursor()
    if inactive is not None:
        # Partial update: only toggle inactive status
        cur2.execute("UPDATE users SET inactive=%s WHERE id=%s", (inactive, user_id))
        diff = "Deactivated" if inactive else "Reactivated"
        log_action(f"{diff} user: {old['name']} | Username: {old['username']}")
    elif password:
        cur2.execute(
            "UPDATE users SET name=%s, username=%s, password=%s, role=%s, email=%s, phone=%s, address=%s, date_hired=%s WHERE id=%s",
            (name, username, hash_password(password), role, email, phone, address, date_hired or None, user_id)
        )
    else:
        cur2.execute(
            "UPDATE users SET name=%s, username=%s, role=%s, email=%s, phone=%s, address=%s, date_hired=%s WHERE id=%s",
            (name, username, role, email, phone, address, date_hired or None, user_id)
        )
    con.commit()
    cur.close()
    cur2.close()
    con.close()

    # ── Build diff log (skip for inactive toggle) ──
    if old and inactive is None:
        changes = []
        if old["name"] != name:
            changes.append(f"Name: '{old['name']}' → '{name}'")
        if old["username"] != username:
            changes.append(f"Username: '{old['username']}' → '{username}'")
        if old["role"] != role:
            changes.append(f"Role: '{old['role']}' → '{role}'")
        if password:
            changes.append("Password: changed")
        diff_str = " | ".join(changes) if changes else "No changes detected"
        log_action(f"Edited user: {name} | {diff_str}")

    return jsonify({"success": True})

@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()

    # ── Fetch user details BEFORE deleting ──
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT name, username, role FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    cur2 = con.cursor()
    cur2.execute("DELETE FROM users WHERE id = %s", (user_id,))
    con.commit()
    cur.close()
    cur2.close()
    con.close()

    if user:
        log_action(
            f"Deleted user: {user['name']} | "
            f"Username: {user['username']} | Role: {user['role']}"
        )

    return jsonify({"success": True})