from flask import Blueprint, render_template, session, redirect, request, jsonify, Response
from db import get_connection
from routes.logger import log_action

maintenance_bp = Blueprint("maintenance", __name__)

# Tables to include in every backup (order matters for restore FK safety)
BACKUP_TABLES = [
    "suppliers",
    "inventory",
    "users",
    "sales",
    "reorder_orders",
    "purchase_orders",
    "order_items",
    "notifications",
    "activity_logs",
]


@maintenance_bp.route("/maintenance")
def maintenance():
    if not session.get("logged_in"):
        return redirect("/")
    if session.get("role", "").lower() != "admin":
        return redirect("/dashboard")
    return render_template(
        "maintenance.html",
        active_page="maintenance",
        role=session.get("role")
    )


# ── Backup Download ────────────────────────────────────────────────────────────

@maintenance_bp.route("/api/maintenance/backup/download", methods=["GET"])
def backup_download():
    """
    Dump all tables to a timestamped JSON file and return it as a download.
    Only admins may trigger this.
    """
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role", "").lower() != "admin":
        return jsonify({"error": "Forbidden"}), 403

    import json
    from datetime import datetime

    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)

        backup_data = {
            "created_at": str(datetime.now()),
            "created_by": session.get("username", "unknown"),
            "database":   "renzrap_db",
            "tables":     {}
        }

        total_rows = 0
        for table in BACKUP_TABLES:
            try:
                cur.execute(f"SELECT * FROM `{table}`")
                rows = cur.fetchall()
                backup_data["tables"][table] = rows
                total_rows += len(rows)
            except Exception:
                # Table may not exist yet — skip gracefully
                backup_data["tables"][table] = []

        cur.close()
        con.close()

        # Also persist an inventory snapshot in the backups table (keeps audit trail)
        try:
            con2 = get_connection()
            cur2 = con2.cursor()
            snapshot_json = json.dumps(
                backup_data["tables"].get("inventory", []), default=str
            )
            cur2.execute(
                "INSERT INTO backups (snapshot, created_by, created_at) VALUES (%s, %s, %s)",
                (snapshot_json, backup_data["created_by"], backup_data["created_at"])
            )
            con2.commit()
            cur2.close()
            con2.close()
        except Exception:
            pass  # backups table optional — don't block the download

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"renzrap_backup_{timestamp}.json"

        log_action(
            f"[MAINTENANCE] Backup downloaded by {backup_data['created_by']} | "
            f"Tables: {len(backup_data['tables'])} | Total rows: {total_rows} | File: {filename}"
        )

        return Response(
            json.dumps(backup_data, default=str, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Restore ───────────────────────────────────────────────────────────────────

@maintenance_bp.route("/api/maintenance/restore", methods=["POST"])
def restore():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role", "").lower() != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    snapshot = data.get("snapshot")
    meta     = data.get("meta", {})

    if not snapshot or not isinstance(snapshot, dict):
        return jsonify({"error": "Invalid or missing snapshot data"}), 400

    # Table restore order (FK safety: parents before children)
    RESTORE_ORDER = [
        "suppliers",
        "users",
        "inventory",
        "sales",
        "reorder_orders",
        "purchase_orders",
        "order_items",
        "notifications",
        "activity_logs",
    ]

    try:
        import json
        from datetime import datetime

        con = get_connection()
        cur = con.cursor(dictionary=True)

        # Get actual columns for each table to avoid mismatch
        def get_columns(table):
            cur.execute(f"SHOW COLUMNS FROM `{table}`")
            return [row["Field"] for row in cur.fetchall()]

        restored_counts = {}

        for table in RESTORE_ORDER:
            rows = snapshot.get(table)
            if rows is None:
                continue
            try:
                columns = get_columns(table)
                cur.execute(f"SET FOREIGN_KEY_CHECKS = 0")
                cur.execute(f"DELETE FROM `{table}`")
                for row in rows:
                    filtered = {k: v for k, v in row.items() if k in columns}
                    if not filtered:
                        continue
                    cols_str = ", ".join(f"`{c}`" for c in filtered)
                    vals_str = ", ".join(["%s"] * len(filtered))
                    cur.execute(
                        f"INSERT INTO `{table}` ({cols_str}) VALUES ({vals_str})",
                        list(filtered.values())
                    )
                restored_counts[table] = len(rows)
            except Exception as table_err:
                restored_counts[table] = f"error: {str(table_err)}"

        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        con.commit()
        cur.close()
        con.close()

        restored_by    = session.get("username", "unknown")
        backup_created = meta.get("created_at", "unknown")

        log_action(
            f"[MAINTENANCE] Full restore from file by {restored_by} | "
            f"Backup created: {backup_created} | "
            f"Tables: {restored_counts}"
        )

        return jsonify({
            "success":           True,
            "records_restored":  restored_counts,
            "backup_created_at": backup_created
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── List available backups ────────────────────────────────────────────────────

@maintenance_bp.route("/api/maintenance/backups", methods=["GET"])
def list_backups():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role", "").lower() != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, created_by, created_at,
                   JSON_LENGTH(snapshot) AS record_count
            FROM backups
            ORDER BY created_at DESC
            LIMIT 50
            """
        )
        rows = cur.fetchall()
        cur.close()
        con.close()

        return jsonify([
            {
                "id":           r["id"],
                "created_by":   r["created_by"],
                "created_at":   str(r["created_at"]),
                "record_count": r["record_count"],
            }
            for r in rows
        ]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500