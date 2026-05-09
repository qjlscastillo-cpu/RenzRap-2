from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
import json
from routes.logger import log_action

sales_bp = Blueprint("sales", __name__)


@sales_bp.route("/sales")
def sales():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("sales.html")


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
            "id":       r["id"],
            "name":     r["item_name"],
            "sku":      r["sku"],
            "category": r["category"],
            "price":    float(r["price"]),
            "stock":    r["quantity"],
             "threshold": r["threshold"],
        })
    return jsonify(products)


# ── POST checkout — save sale & deduct stock ──────────────────────────────────
def generate_receipt_number(cur):
    cur.execute("SELECT id FROM sales ORDER BY sold_at DESC LIMIT 1")
    row = cur.fetchone()
    if not row or not row['id']:
        return "aa000000"

    last    = row['id']
    letters = last[:2]
    digits  = int(last[2:]) + 1

    if digits > 999999:
        digits = 0
        l1, l2 = letters[0], letters[1]
        if l2 == 'z':
            l2 = 'a'
            l1 = chr(ord(l1) + 1)
        else:
            l2 = chr(ord(l2) + 1)
        letters = l1 + l2

    return f"{letters}{digits:06d}"


@sales_bp.route("/api/sales/checkout", methods=["POST"])
def checkout():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data       = request.get_json()
    items      = data.get("items", [])
    is_discounted = data.get("discount", False)
    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    # Calculate totals
    subtotal   = sum(i["price"] * i["qty"] for i in items)
    discount   = round(subtotal * 0.20, 2) if is_discounted else 0
    vat        = round(subtotal * 0.12, 2)
    total      = round(subtotal - discount + vat, 2)

    con = get_connection()
    cur = con.cursor(dictionary=True)
    receipt_id = generate_receipt_number(cur)

    cur = con.cursor()

    # One row for the whole transaction
    cur.execute(
    """INSERT INTO sales (id, items, subtotal, vat, total_price)
       VALUES (%s, %s, %s, %s, %s)""",
    (receipt_id, json.dumps(items), subtotal, vat, total)
)

    # Deduct stock for each item
    for item in items:
        cur.execute(
            "UPDATE inventory SET quantity = quantity - %s WHERE id = %s",
            (item["qty"], item["id"])
        )

    con.commit()
    item_names = ", ".join([f"{i['qty']}x {i['name']}" for i in items])
    log_action(f"Processed sale: {item_names}")
    cur.close()
    con.close()
    return jsonify({"success": True})