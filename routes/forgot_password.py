import random
from flask import Blueprint, request, jsonify, session, render_template, redirect
from db import get_connection, hash_password
from routes.notification_service import create_notification

forgot_bp = Blueprint("forgot", __name__)

def get_all_admins():
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT username FROM users WHERE role = 'Admin' AND inactive = 0")
    admins = cur.fetchall()
    cur.close()
    con.close()
    return [a["username"] for a in admins]

@forgot_bp.route("/forgot-password", methods=["GET"])
def forgot_page():
    return render_template("forgot_password.html")

@forgot_bp.route("/api/forgot-password/request", methods=["POST"])
def request_reset():
    data = request.get_json()
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username is required."}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if not user:
        cur.close()
        con.close()
        return jsonify({"success": False, "message": "User not found."}), 404

    code = str(random.randint(100000, 999999))
    cur.execute(
        "INSERT INTO password_reset_codes (username, reset_code) VALUES (%s, %s)",
        (username, code)
    )
    con.commit()
    cur.close()
    con.close()

    admins = get_all_admins()
    for admin in admins:
        create_notification(admin, "password_reset",
            f"Password reset requested by {username} (Name: {user['name']}). Code: {code}",
            link="/admin/password-resets")

    return jsonify({"success": True, "message": "Reset code sent to admins."})

@forgot_bp.route("/api/forgot-password/reset", methods=["POST"])
def reset_password():
    data = request.get_json()
    username = data.get("username", "").strip()
    code = data.get("code", "").strip()
    new_password = data.get("new_password", "")

    if not username or not code or not new_password:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if len(new_password) > 8:
        return jsonify({"success": False, "message": "Password must be 8 characters or less."}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute(
        "SELECT id FROM password_reset_codes WHERE username = %s AND reset_code = %s AND used = 0",
        (username, code)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        con.close()
        return jsonify({"success": False, "message": "Invalid or already used code."}), 400

    cur.execute("UPDATE password_reset_codes SET used = 1 WHERE id = %s", (row["id"],))
    cur.execute("UPDATE users SET password = %s WHERE username = %s",
                (hash_password(new_password), username))
    con.commit()
    cur.close()
    con.close()

    return jsonify({"success": True, "message": "Password updated successfully."})

@forgot_bp.route("/admin/password-resets")
def admin_resets_page():
    if not session.get("logged_in"):
        return redirect("/")
    if session.get("role", "").lower() != "admin":
        return redirect("/dashboard")
    return render_template("admin_resets.html", active_page="admin_resets", role=session.get("role"))

@forgot_bp.route("/api/forgot-password/pending", methods=["GET"])
def get_pending_resets():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT r.id, r.username, u.name, r.reset_code, r.created_at
        FROM password_reset_codes r
        JOIN users u ON u.username = r.username
        WHERE r.used = 0
        ORDER BY r.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    for r in rows:
        r["created_at"] = r["created_at"].strftime("%b %d, %Y %I:%M %p") if r["created_at"] else ""
    return jsonify(rows)

@forgot_bp.route("/api/forgot-password/<int:reset_id>", methods=["DELETE"])
def delete_pending_reset(reset_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM password_reset_codes WHERE id = %s", (reset_id,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})
