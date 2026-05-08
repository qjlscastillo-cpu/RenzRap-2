from flask import Flask, request, jsonify, redirect, session, render_template, url_for
import mysql.connector
import hashlib
import webbrowser
from threading import Timer


app = Flask(__name__)
app.secret_key = "renzrap_secret_key"


# ── Database Config ─────────────────────────────────────────────────────────


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "00000000",   # ← change this to your MySQL password
    "database": "renzrap_db"
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    con = get_connection()
    cur = con.cursor()


    # ── Users ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(150) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    """)


    # ── Inventory ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            quantity INT DEFAULT 0,
            price DECIMAL(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ── Sales ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            quantity_sold INT NOT NULL,
            total_price DECIMAL(10, 2) NOT NULL,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ── Seed default admin user ────────────────────────────────────────────
    cur.execute("SELECT 1 FROM users WHERE username = %s", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            ("admin", hash_password("password123"))
        )


    con.commit()
    cur.close()
    con.close()
    print("✅ Database initialized — all tables ready.")


def verify_user(username: str, password: str) -> bool:
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

@app.route("/sales")
def sales():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("sales.html")

@app.route("/profile")
def profile():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("profile.html")

@app.route("/about-us")
def about_us():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))
    return render_template("aboutus.html")

# Placeholder routes (Removed /about and /aboutus from here)
@app.route("/maintenance")
@app.route("/security")
@app.route("/faqs")
def placeholder():
    page = request.path.strip("/").capitalize()
    return f"<h2 style='font-family:sans-serif;padding:40px'>{page} page coming soon. <a href='/dashboard'>Back to Dashboard</a></h2>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ── DB Test ────────────────────────────────────────────────────────────────
@app.route("/db-test")
def db_test():
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        cur.close()
        con.close()
        return f"<h2>✅ Database connected! Users in table: {count}</h2>"
    except Exception as e:
        return f"<h2>❌ Connection failed: {str(e)}</h2>"
# ── Run ────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    init_db()
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("Running at http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
