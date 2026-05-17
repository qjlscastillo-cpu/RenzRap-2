from flask import Blueprint, render_template, session, redirect, jsonify
from db import get_connection

security_bp = Blueprint("security", __name__)

@security_bp.route("/security")
def security():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("security.html")

@security_bp.route("/api/security/logs", methods=["GET"])
def get_logs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    # No LIMIT — return every log entry so the frontend can
    # group them by user+day without missing older records.
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