import json
from flask import Blueprint, session, request, jsonify
from db import get_connection
from datetime import datetime, timedelta

reports_bp = Blueprint("reports", __name__)


def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except (ValueError, AttributeError):
        return None


@reports_bp.route("/api/reports/sales", methods=["GET"])
def sales_report():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    period = request.args.get("period", "daily")
    start  = parse_date(request.args.get("start"))
    end    = parse_date(request.args.get("end"))
    today  = datetime.now().date()

    if not start:
        if period == "daily":
            start = today
        elif period == "weekly":
            start = today - timedelta(days=today.weekday())
        elif period == "monthly":
            start = today.replace(day=1)
        else:
            start = today.replace(month=1, day=1)
    if not end:
        end = today if period != "yearly" else today.replace(month=12, day=31)

    if start > end:
        return jsonify({"error": "Start date cannot be after end date"}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)

    # ── Summary ──
    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total,
               COUNT(*) AS count,
               COALESCE(SUM(total_price) / NULLIF(COUNT(*), 0), 0) AS avg
        FROM sales
        WHERE DATE(sold_at) BETWEEN %s AND %s
    """, (start, end))
    summary = cur.fetchone()

    # ── Rows ──
    if period == "daily":
        cur.execute("""
            SELECT id, items, total_price, sold_at
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            ORDER BY sold_at DESC
        """, (start, end))
        raw = cur.fetchall()
        rows = []
        for r in raw:
            items_list = []
            try:
                items_list = json.loads(r["items"]) if r["items"] else []
            except Exception:
                pass
            items_str = ", ".join([f"{i.get('qty','?')}x {i.get('name','?')}" for i in items_list])
            rows.append({
                "receipt": r["id"],
                "time":    r["sold_at"].strftime("%I:%M %p") if r["sold_at"] else "",
                "items":   items_str,
                "total":   float(r["total_price"]),
            })

    elif period == "weekly":
        cur.execute("""
            SELECT DATE(sold_at) AS day,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY DATE(sold_at) ORDER BY day
        """, (start, end))
        raw = cur.fetchall()
        rows = []
        for r in raw:
            rows.append({
                "label": r["day"].strftime("%m/%d/%Y") if r["day"] else "?",
                "day_name": r["day"].strftime("%A") if r["day"] else "",
                "count": r["count"],
                "total": float(r["total"]),
            })

    elif period == "monthly":
        cur.execute("""
            SELECT DATE(sold_at) AS day,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY DATE(sold_at) ORDER BY day
        """, (start, end))
        raw = cur.fetchall()
        rows = []
        for r in raw:
            rows.append({
                "label": r["day"].strftime("%m/%d/%Y") if r["day"] else "?",
                "count": r["count"],
                "total": float(r["total"]),
            })

    else:
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        cur.execute("""
            SELECT YEAR(sold_at) AS yr, MONTH(sold_at) AS mo,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY YEAR(sold_at), MONTH(sold_at) ORDER BY yr, mo
        """, (start, end))
        raw = cur.fetchall()
        rows = []
        for r in raw:
            rows.append({
                "label": f"{month_names[r['mo']-1]} {r['yr']}",
                "count": r["count"],
                "total": float(r["total"]),
            })

    cur.close()
    con.close()

    return jsonify({
        "period":  period,
        "summary": {
            "total_sales": float(summary["total"]),
            "count":       summary["count"],
            "avg_sale":    float(summary["avg"]),
            "start":       start.strftime("%m/%d/%Y"),
            "end":         end.strftime("%m/%d/%Y"),
        },
        "rows": rows,
    })


@reports_bp.route("/api/reports/inventory", methods=["GET"])
def inventory_report():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM inventory")
    total_products = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS cnt FROM inventory WHERE quantity <= 0")
    out_of_stock = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT COUNT(*) AS cnt FROM inventory
        WHERE quantity > 0 AND quantity <= threshold
    """)
    low_stock = cur.fetchone()["cnt"]

    in_stock = total_products - out_of_stock - low_stock

    cur.execute("SELECT COALESCE(SUM(price * quantity), 0) AS total FROM inventory")
    total_value = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT * FROM inventory
        ORDER BY item_name ASC
    """)
    rows = cur.fetchall()

    cur.execute("""
        SELECT id, item_name, sku, barcode, category,
               quantity, price, threshold, created_at
        FROM inventory
        ORDER BY created_at DESC LIMIT 10
    """)
    recent = cur.fetchall()
    cur.close()
    con.close()

    products = []
    for r in rows:
        qty = r["quantity"]
        thr = r["threshold"]
        if qty <= 0:
            status = "Out of Stock"
        elif qty <= thr:
            status = "Low Stock"
        else:
            status = "In Stock"
        products.append({
            "id":       r["id"],
            "name":     r["item_name"],
            "sku":      r["sku"],
            "barcode":  r["barcode"] or "",
            "category": r["category"],
            "quantity": qty,
            "price":    float(r["price"]),
            "threshold": thr,
            "status":   status,
        })

    recent_refills = []
    for r in recent:
        recent_refills.append({
            "name":      r["item_name"],
            "sku":       r["sku"],
            "quantity":  r["quantity"],
            "created":   r["created_at"].strftime("%m/%d/%Y") if r["created_at"] else "",
        })

    return jsonify({
        "summary": {
            "total_products": total_products,
            "total_value":    total_value,
            "in_stock":       in_stock,
            "low_stock":      low_stock,
            "out_of_stock":   out_of_stock,
        },
        "products":      products,
        "recent_refills": recent_refills,
    })
