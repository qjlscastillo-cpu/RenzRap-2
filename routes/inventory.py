from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from routes.logger import log_action

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/inventory")
def inventory():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("inventory.html")


@inventory_bp.route("/api/inventory", methods=["GET"])
def get_inventory():
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
            "category":  r["category"],
            "price":     float(r["price"]),
            "qty":       r["quantity"],
            "threshold": r["threshold"]
        })
    return jsonify(products)


@inventory_bp.route("/api/inventory", methods=["POST"])
def add_product():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """INSERT INTO inventory (item_name, sku, category, price, quantity, threshold)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["name"], data["sku"], data["category"],
         data["price"], data["qty"], data["threshold"])
    )
    con.commit()
    new_id = cur.lastrowid
    cur.close()
    con.close()
    log_action(f"Added product: {data['name']} (SKU: {data['sku']})")
    return jsonify({"id": new_id, **data}), 201


@inventory_bp.route("/api/inventory/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """UPDATE inventory
           SET item_name=%s, sku=%s, category=%s, price=%s, quantity=%s, threshold=%s
           WHERE id=%s""",
        (data["name"], data["sku"], data["category"],
         data["price"], data["qty"], data["threshold"], product_id)
    )
    con.commit()
    cur.close()
    con.close()
    log_action(f"Updated product ID {product_id}: {data['name']}")
    return jsonify({"success": True})


@inventory_bp.route("/api/inventory/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM inventory WHERE id=%s", (product_id,))
    con.commit()
    cur.close()
    con.close()
    log_action(f"Deleted product ID {product_id}")
    return jsonify({"success": True})


@inventory_bp.route("/api/dashboard/transactions", methods=["GET"])
def get_transactions():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT item_name, quantity, threshold, created_at
        FROM inventory
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        qty = r["quantity"]
        threshold = r["threshold"]
        if qty <= 0:
            status = "Out of Stock"
        elif qty <= threshold:
            status = "Low Stock"
        else:
            status = "In Stock"
        result.append({
            "item_name":  r["item_name"],
            "created_at": str(r["created_at"]),
            "quantity":   qty,
            "status":     status
        })
    return jsonify(result)