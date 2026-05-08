from flask import Flask, request, jsonify, redirect, session, render_template, url_for
import sqlite3
import hashlib
import webbrowser
from threading import Timer

app = Flask(__name__)
app.secret_key = "renzrap_secret_key"

DB_PATH = "users.db"

# ── Database ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    cur.execute("SELECT 1 FROM users WHERE username = ?", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", hash_password("password123"))
        )
    con.commit()
    con.close()

def verify_user(username: str, password: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT 1 FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    )
    result = cur.fetchone() is not None
    con.close()
    return result

# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if verify_user(username, password):
        session["logged_in"] = True
        session["username"] = username
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid username or password."})

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("dashboard.html")

@app.route("/inventory")
def inventory():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("inventory.html")

# --- NEW SALES ROUTE ADDED HERE ---
@app.route("/sales")
def sales():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("sales.html")
# ----------------------------------

# Placeholder routes — removed /sales from here
@app.route("/profile")
@app.route("/maintenance")
@app.route("/security")
@app.route("/about")
@app.route("/faqs")
def placeholder():
    page = request.path.strip("/").capitalize()
    return f"<h2 style='font-family:sans-serif;padding:40px'>{page} page coming soon. <a href='/dashboard'>Back to Dashboard</a></h2>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("Running at http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
    
    masi