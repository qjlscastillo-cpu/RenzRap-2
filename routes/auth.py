from flask import Blueprint, request, jsonify, redirect, session, render_template, url_for
from db import get_connection, hash_password

auth_bp = Blueprint("auth", __name__)

def verify_user(username, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT 1 FROM users WHERE username = %s AND password = %s",
        (username, hash_password(password))
    )
    result = cur.fetchone() is not None
    cur.close()
    con.close()
    return result

@auth_bp.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if verify_user(username, password):
        session["logged_in"] = True
        session["username"] = username
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid username or password."})

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))