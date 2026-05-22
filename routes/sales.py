from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from datetime import date, timedelta
import json
from routes.logger import log_action
from routes.notification_service import create_notification

sales_bp = Blueprint("sales", __name__)


@sales_bp.route("/sales")
def sales():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("sales.html", active_page="sales", role=session.get("role"))


# ── GET inventory products for the POS ───────────────────────────────────────
@sales_bp.route("/api/sales/products", methods=["GET"])
def get_products():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM inventory ORDER BY item_name ASC")
    rows = cur.fetchall()
    cur.close()
    con.close()
    products = []
    for r in rows:
        products.append({
            "id":        r["id"],
            "name":      r["item_name"],
            "sku":       r["sku"],
            "barcode":   r["barcode"],
            "category":  r["category"],
            "price":     float(r["price"]),
            "stock":     r["quantity"],
            "threshold": r["threshold"],
        })
    return jsonify(products)


# ── POST checkout — save sale & deduct stock ──────────────────────────────────
def generate_receipt_number(cur):
    cur.execute("SELECT id FROM sales ORDER BY sold_at DESC LIMIT 1")
    row = cur.fetchone()
    if not row or not row['id']:
        return "aaa000000"

    last = row['id']

    if len(last) < 9:
        return "aaa000000"

    letters = last[:3]
    digits  = int(last[3:]) + 1

    if digits > 999999:
        digits = 0
        l1, l2, l3 = letters[0], letters[1], letters[2]
        if l3 == 'z':
            l3 = 'a'
            if l2 == 'z':
                l2 = 'a'
                l1 = chr(ord(l1) + 1)
            else:
                l2 = chr(ord(l2) + 1)
        else:
            l3 = chr(ord(l3) + 1)
        letters = l1 + l2 + l3

    return f"{letters}{digits:06d}"


@sales_bp.route("/api/sales/checkout", methods=["POST"])
def checkout():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data          = request.get_json()
    items         = data.get("items", [])
    is_discounted = data.get("discount", False)
    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    subtotal = sum(i["price"] * i["qty"] for i in items)
    discount = round(subtotal * 0.20, 2) if is_discounted else 0
    vat      = round(subtotal * 0.12, 2)
    total    = round(subtotal - discount + vat, 2)

    con = get_connection()
    cur = con.cursor(dictionary=True)
    receipt_id = generate_receipt_number(cur)

    cur = con.cursor()
    cur.execute(
        """INSERT INTO sales (id, items, subtotal, vat, total_price)
           VALUES (%s, %s, %s, %s, %s)""",
        (receipt_id, json.dumps(items), subtotal, vat, total)
    )
    for item in items:
        cur.execute(
            "UPDATE inventory SET quantity = quantity - %s WHERE id = %s",
            (item["qty"], item["id"])
        )

    con.commit()
    item_names = ", ".join([f"{i['qty']}x {i['name']}" for i in items])
    log_action(f"Processed sale: {item_names} ({receipt_id})")
    
    # ✅ ADD THIS
    create_notification(
        username=session.get('username'),
        notif_type='sale',
        message=f'Sale #{receipt_id}: {item_names} — ₱{total:,.2f}',
        link='/sales'
    )
    cur.close()
    con.close()
    return jsonify({"success": True, "receipt_number": receipt_id})

@sales_bp.route("/api/sales/next-receipt-id", methods=["GET"])
def next_receipt_id():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    receipt_id = generate_receipt_number(cur)
    cur.close()
    con.close()
    return jsonify({"receipt_id": receipt_id})

# ── GET dashboard summary (today / month / year totals) ──────────────────────
@sales_bp.route("/api/dashboard/summary", methods=["GET"])
def dashboard_summary():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total
        FROM sales WHERE DATE(sold_at) = CURDATE()
    """)
    today = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total
        FROM sales
        WHERE YEAR(sold_at) = YEAR(CURDATE()) AND MONTH(sold_at) = MONTH(CURDATE())
    """)
    month = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0) AS total
        FROM sales WHERE YEAR(sold_at) = YEAR(CURDATE())
    """)
    year = float(cur.fetchone()["total"])

    cur.close()
    con.close()
    return jsonify({"today": today, "month": month, "year": year})


# ── GET dashboard chart data ──────────────────────────────────────────────────
@sales_bp.route("/api/dashboard/chart", methods=["GET"])
def dashboard_chart():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    period = request.args.get("period", "daily")
    con    = get_connection()
    cur    = con.cursor(dictionary=True)

    if period == "daily":
        # Rolling last 7 days (6 days ago → today)
        today      = date.today()
        week_start = today - timedelta(days=6)

        cur.execute("""
            SELECT DATE(sold_at) AS day, COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE DATE(sold_at) BETWEEN %s AND %s
            GROUP BY DATE(sold_at)
        """, (week_start, today))

        rows      = cur.fetchall()
        sales_map = {str(r["day"]): float(r["total"]) for r in rows}

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        labels, values = [], []
        for i in range(7):
            d         = week_start + timedelta(days=i)
            day_label = day_names[d.weekday()]          # 0=Mon … 6=Sun
            labels.append(f"{day_label} {d.month}/{d.day}/{d.year}")
            values.append(sales_map.get(str(d), 0))

    elif period == "monthly":
        # Last 6 months
        today = date.today()
        cur.execute("""
            SELECT YEAR(sold_at) AS yr, MONTH(sold_at) AS mo,
                   COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE sold_at >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 5 MONTH), '%Y-%m-01')
            GROUP BY YEAR(sold_at), MONTH(sold_at)
        """)
        rows      = cur.fetchall()
        sales_map = {(int(r["yr"]), int(r["mo"])): float(r["total"]) for r in rows}

        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        labels, values = [], []
        for i in range(5, -1, -1):
            total_m = today.year * 12 + today.month - 1 - i
            yr = total_m // 12
            mo = total_m % 12 + 1
            labels.append(f"{month_names[mo-1]} {yr}")
            values.append(sales_map.get((yr, mo), 0))

    elif period == "yearly":
        # Last 5 years
        today = date.today()
        cur.execute("""
            SELECT YEAR(sold_at) AS yr, COALESCE(SUM(total_price), 0) AS total
            FROM sales
            WHERE YEAR(sold_at) BETWEEN %s AND %s
            GROUP BY YEAR(sold_at)
        """, (today.year - 4, today.year))
        rows      = cur.fetchall()
        sales_map = {int(r["yr"]): float(r["total"]) for r in rows}

        labels, values = [], []
        for i in range(4, -1, -1):
            yr = today.year - i
            labels.append(str(yr))
            values.append(sales_map.get(yr, 0))

    else:
        cur.close()
        con.close()
        return jsonify({"error": "Invalid period"}), 400

    cur.close()
    con.close()
    return jsonify({"labels": labels, "values": values})

# ── GET history (sales log) ──────────────────────────────────────────────────
@sales_bp.route("/api/history", methods=["GET"])
def get_history():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT id, items, subtotal, vat, total_price, sold_at
        FROM sales
        ORDER BY sold_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()

    result = []
    for r in rows:
        try:
            items = json.loads(r["items"]) if r["items"] else []
        except:
            items = []
        result.append({
            "ref":        r["id"],
            "items":      items,
            "subtotal":   float(r["subtotal"] or 0),
            "vat":        float(r["vat"] or 0),
            "amount":     float(r["total_price"] or 0),
            "created_at": r["sold_at"].isoformat() if r["sold_at"] else None,
        })
    return jsonify(result)