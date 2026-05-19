from flask import Blueprint, render_template, session, redirect, jsonify
from db import get_connection

security_bp = Blueprint("security", __name__)


def create_logs_table():
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                username   VARCHAR(150),
                role       VARCHAR(50),
                action     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()
        # ensure action column is TEXT (widen if needed)
        try:
            cur.execute("ALTER TABLE activity_logs MODIFY COLUMN action TEXT")
            con.commit()
        except Exception:
            pass
        cur.close()
        con.close()
    except Exception as e:
        print(f"create_logs_table error: {e}")


def log_action(action: str, username: str = None, role: str = None):
    try:
        if username is None:
            username = session.get("username", "Unknown")
        if role is None:
            role = session.get("role", "Unknown")
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO activity_logs (username, role, action) VALUES (%s, %s, %s)",
            (username, role, action)
        )
        con.commit()
        cur.close()
        con.close()
    except Exception as e:
        print(f"log_action error: {e}")


# Ensure logs table exists when security module loads
create_logs_table()

@security_bp.route("/security")
def security():
    if not session.get("logged_in"):
        return redirect("/")
    if session.get("role", "").lower() != "admin":
        return redirect("/dashboard")
    return render_template("security.html", active_page="security", role=session.get("role"))

@security_bp.route("/api/security/logs", methods=["GET"])
def get_logs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT username, role, action, created_at
        FROM activity_logs
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    return jsonify([
        {
            "username":   r["username"],
            "role":       r["role"],
            "action":     r["action"],
            "created_at": str(r["created_at"])
        }
        for r in rows
    ])