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
    cur.execute("""
        SELECT username, role, action, created_at
        FROM activity_logs
        ORDER BY created_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        result.append({
            "username":   r["username"],
            "role":       r["role"],
            "action":     r["action"],
            "created_at": str(r["created_at"])
        })
    return jsonify(result)