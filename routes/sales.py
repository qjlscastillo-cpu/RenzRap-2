from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection

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
            "stock":    r["quantity"]
        })
    return jsonify(products)


# ── POST checkout — save sale & deduct stock ──────────────────────────────────
@sales_bp.route("/api/sales/checkout", methods=["POST"])
def checkout():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    con = get_connection()
    cur = con.cursor()

    for item in items:
        # Save to sales table
        cur.execute(
            "INSERT INTO sales (item_name, quantity_sold, total_price) VALUES (%s, %s, %s)",
            (item["name"], item["qty"], item["price"] * item["qty"])
        )
        # Deduct from inventory
        cur.execute(
            "UPDATE inventory SET quantity = quantity - %s WHERE id = %s",
            (item["qty"], item["id"])
        )

    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})