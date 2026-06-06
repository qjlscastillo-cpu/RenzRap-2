import json
from flask import Blueprint, session, request, jsonify
from db import get_connection
from datetime import datetime, timedelta

reports_bp = Blueprint("reports", __name__)

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except (ValueError, AttributeError):
        return None


def iso_week(d):
    """Return week-of-month label (1-4)."""
    return f"Week {(d.day - 1) // 7 + 1}"


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
            # Sunday of current week
            start = today - timedelta(days=(today.weekday() + 1) % 7)
        elif period == "monthly":
            start = today.replace(day=1)
        else:
            start = today.replace(month=1, day=1)
    if not end:
        if period == "weekly":
            # Saturday of current week
            start_wk = today - timedelta(days=(today.weekday() + 1) % 7)
            end = start_wk + timedelta(days=6)
        elif period == "monthly":
            import calendar
            _, last = calendar.monthrange(today.year, today.month)
            end = today.replace(day=last)
        elif period == "yearly":
            end = today.replace(month=12, day=31)
        else:
            end = today

    if start > end:
        return jsonify({"error": "Start date cannot be after end date"}), 400

    con = get_connection()
    cur = con.cursor(dictionary=True)

    # ── Summary ──
    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total,
               COUNT(*) AS count
        FROM sales
        WHERE DATE(sold_at) BETWEEN %s AND %s
    """, (start, end))
    summary = cur.fetchone()
    total_sales = float(summary["total"])
    tx_count = summary["count"]

    # Build avg divisor per period
    if period == "weekly":
        num_periods = 7  # avg per day
        avg_label = "Avg Sale/Day"
    elif period == "monthly":
        num_periods = 4  # avg per week
        avg_label = "Avg Sale/Week"
    elif period == "yearly":
        num_periods = 12  # avg per month
        avg_label = "Avg Sale/Month"
    else:
        num_periods = max(tx_count, 1)
        avg_label = "Avg Sale"

    avg_sale = total_sales / num_periods if num_periods else 0

    rows = []

    if period == "daily":
        # Individual transactions — no items column
        cur.execute("""
            SELECT id, total_price, sold_at
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            ORDER BY sold_at DESC
        """, (start, end))
        for r in cur.fetchall():
            rows.append({
                "receipt": r["id"],
                "time":    r["sold_at"].strftime("%I:%M %p") if r["sold_at"] else "",
                "total":   float(r["total_price"]),
            })

    elif period == "weekly":
        # 7-day grid Sun–Sat
        week_start = start - timedelta(days=start.weekday())  # align to Monday internally
        # But start is already Sunday, so use start directly
        day_map = {}
        cur.execute("""
            SELECT DATE(sold_at) AS day,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY DATE(sold_at)
        """, (start, end))
        for r in cur.fetchall():
            day_map[r["day"]] = {"count": r["count"], "total": float(r["total"])}

        for i in range(7):
            d = start + timedelta(days=i)
            data = day_map.get(d, {"count": 0, "total": 0})
            rows.append({
                "label": d.strftime("%m/%d/%Y"),
                "count": data["count"],
                "total": data["total"],
            })
    elif period == "monthly":
        # 4-week buckets within the month
        week_map = {}
        cur.execute("""
            SELECT DATE(sold_at) AS sale_date,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY DATE(sold_at)
        """, (start, end))
        for r in cur.fetchall():
            wk = iso_week(r["sale_date"])
            if wk not in week_map:
                week_map[wk] = {"count": 0, "total": 0}
            week_map[wk]["count"] += r["count"]
            week_map[wk]["total"] += float(r["total"])

        for w in range(1, 5):
            ws = start + timedelta(days=(w - 1) * 7)
            we = min(start + timedelta(days=w * 7 - 1), end)
            if ws > end:
                break
            label = f"{ws.strftime('%m/%d/%Y')} – {we.strftime('%m/%d/%Y')}"
            data = week_map.get(f"Week {w}", {"count": 0, "total": 0})
            rows.append({
                "label": label,
                "count": data["count"],
                "total": data["total"],
            })

    else:  # yearly
        # 12-month grid
        month_map = {}
        cur.execute("""
            SELECT YEAR(sold_at) AS yr, MONTH(sold_at) AS mo,
                   COUNT(*) AS count,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY YEAR(sold_at), MONTH(sold_at)
        """, (start, end))
        for r in cur.fetchall():
            key = (r["yr"], r["mo"])
            month_map[key] = {"count": r["count"], "total": float(r["total"])}

        for m in range(1, 13):
            label = MONTH_NAMES[m - 1]
            data = month_map.get((start.year if start else today.year, m), {"count": 0, "total": 0})
            rows.append({
                "label": label,
                "count": data["count"],
                "total": data["total"],
            })

    # ── Best Seller ──
    best_seller = None
    if tx_count > 0:
        cur.execute("""
            SELECT items FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s AND items IS NOT NULL
        """, (start, end))
        item_counts = {}
        for row in cur.fetchall():
            items_json = row["items"]
            if not items_json:
                continue
            try:
                item_list = json.loads(items_json)
                for it in item_list:
                    name = it.get("name", "Unknown")
                    qty = it.get("quantity", 1)
                    item_counts[name] = item_counts.get(name, 0) + qty
            except (json.JSONDecodeError, TypeError):
                pass
        if item_counts:
            top_name = max(item_counts, key=item_counts.get)
            best_seller = {"name": top_name, "quantity": item_counts[top_name]}

    cur.close()
    con.close()

    return jsonify({
        "period":     period,
        "avg_label":  avg_label,
        "best_seller": best_seller,
        "summary": {
            "total_sales": total_sales,
            "count":       tx_count,
            "avg_sale":    round(avg_sale, 2),
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
