from flask import Blueprint, request, jsonify, redirect, session, render_template, url_for
from db import get_connection, hash_password
from routes.logger import log_action

auth_bp = Blueprint("auth", __name__)

def verify_user(username, password):
    con = get_connection()
    cur = con.cursor(dictionary=True)  # changed to dictionary=True to get full user info
    cur.execute(
        "SELECT id, name, username, role FROM users WHERE username = %s AND password = %s",
        (username, hash_password(password))
    )
    result = cur.fetchone()
    cur.close()
    con.close()
    return result  # returns full user dict or None

@auth_bp.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user = verify_user(username, password)
    if user:
        session["logged_in"] = True
        session["username"]  = user["username"]
        session["role"]      = user["role"]
        session["name"]      = user["name"]
        log_action("Logged in")
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid username or password."})

@auth_bp.route("/logout")
def logout():
    log_action("Logged out")  # log before clearing session
    session.clear()
    return redirect(url_for("auth.login_page"))