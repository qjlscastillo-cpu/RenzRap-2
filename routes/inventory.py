import json, math
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from routes.logger import log_action
from routes.notification_service import create_notification, check_low_stock

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/inventory")
def inventory():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("inventory.html", active_page="inventory", role=session.get("role"))
@inventory_bp.route("/api/inventory", methods=["GET"])
def get_inventory():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT i.*, s.name AS supplier_name
        FROM inventory i
        LEFT JOIN suppliers s ON s.id = i.supplier_id
        ORDER BY i.item_name ASC
    """)
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
            "qty":       r["quantity"],
            "threshold": r["threshold"],
            "inactive":  bool(r.get("inactive", False)),
            "supplier_id": r["supplier_id"],
            "supplier_name": r["supplier_name"] or '',
        })
    return jsonify(products)


@inventory_bp.route("/api/inventory/<int:product_id>/suggested-threshold", methods=["GET"])
def suggested_threshold(product_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    con = get_connection()
    cur = con.cursor(dictionary=True)

    # Get product and its supplier's delivery_time
    cur.execute("""
        SELECT i.id, i.item_name, i.threshold, i.supplier_id,
               COALESCE(s.delivery_time, 0) AS delivery_time
        FROM inventory i
        LEFT JOIN suppliers s ON s.id = i.supplier_id
        WHERE i.id = %s
    """, (product_id,))
    product = cur.fetchone()
    if not product:
        cur.close(); con.close()
        return jsonify({"error": "Product not found"}), 404

    dt = max(product['delivery_time'] or 0, 2)

    # Fetch sales for this product (last 90 days)
    cur.execute("""
        SELECT items, sold_at
        FROM sales
        WHERE sold_at >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        ORDER BY sold_at ASC
    """)
    sales_rows = cur.fetchall()
    cur.close(); con.close()

    # Aggregate qty for this product
    total_qty = 0
    for row in sales_rows:
        try:
            for item in json.loads(row['items']):
                if item['id'] == product_id:
                    total_qty += int(item['qty'])
        except Exception:
            pass

    if total_qty == 0 or not sales_rows:
        return jsonify({"suggested": None, "message": "No sales data yet"})

    # Compute actual date range
    first_date = sales_rows[0]['sold_at']
    last_date  = sales_rows[-1]['sold_at']
    if isinstance(first_date, datetime):
        actual_days = min(90, max((last_date - first_date).days + 1, 1))
    else:
        actual_days = 90

    avg_daily = total_qty / actual_days
    suggested = max(math.ceil(avg_daily * dt * 1.5), 2)

    return jsonify({
        "suggested": suggested,
        "avg_daily_sales": round(avg_daily, 2),
        "delivery_time": dt,
        "current_threshold": product['threshold'] or 0,
        "message": f"Based on {round(avg_daily,2)} avg daily sales × {dt} day delivery × 1.5x buffer"
    })


@inventory_bp.route("/api/inventory", methods=["POST"])
def add_product():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role", "").lower() != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json()
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """INSERT INTO inventory (item_name, sku, barcode, category, supplier_id, price, quantity, threshold)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data["name"], data["sku"], data.get("barcode", "").strip(),
         data["category"], data.get("supplier_id"),
         data["price"], data["qty"], data["threshold"])
    )
    con.commit()
    try:
        create_notification(
            username=session.get('username'),
            notif_type='inventory',
            message=f"New item added: {data['name']} | Qty: {data['qty']} | P{float(data['price']):.2f}",
            link='/inventory'
        )
    except Exception as e:
        pass
    new_id = cur.lastrowid
    cur.close()
    con.close()

    log_action(
        f"[INVENTORY] Added item: {data['name']} | "
        f"SKU: {data['sku']} | Category: {data['category']} | "
        f"Price: ₱{float(data['price']):.2f} | "
        f"Qty: {data['qty']} | Threshold: {data['threshold']}"
    )
    try:
        check_low_stock()
    except Exception:
        pass
    return jsonify({"id": new_id, **data}), 201


@inventory_bp.route("/api/inventory/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()

    # ── Fetch old values BEFORE updating ──
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM inventory WHERE id=%s", (product_id,))
    old = cur.fetchone()

    cur2 = con.cursor()
    cur2.execute(
    """UPDATE inventory
       SET item_name=%s, sku=%s, barcode=%s, category=%s, supplier_id=%s,
           price=%s, quantity=%s, threshold=%s, inactive=%s
       WHERE id=%s""",
    (data["name"], data["sku"], data.get("barcode", "").strip(),
     data["category"], data.get("supplier_id"),
     data["price"], data["qty"],
     data["threshold"], int(data.get("inactive", False)),
     product_id)
)
    
    con.commit()
    create_notification(
        username=session.get('username'),
        notif_type='inventory',
        message=f"Item updated: {data['name']} | Qty: {data['qty']} | P{float(data['price']):.2f}",
        link='/inventory'
    )
    cur.close()
    cur2.close()
    con.close()

    # ── Build a diff log so the audit trail is meaningful ──
    if old:
        changes = []
        if old["item_name"] != data["name"]:
            changes.append(f"Name: '{old['item_name']}' -> '{data['name']}'")
        if old["sku"] != data["sku"]:
            changes.append(f"SKU: '{old['sku']}' -> '{data['sku']}'")
        if str(old.get("barcode", "") or "") != str(data.get("barcode", "") or ""):
            changes.append(f"Barcode: '{old.get('barcode','')}' -> '{data.get('barcode','')}'")
        if old["category"] != data["category"]:
            changes.append(f"Category: '{old['category']}' -> '{data['category']}'")
        if int(old.get("supplier_id") or 0) != int(data.get("supplier_id") or 0):
            changes.append(f"Supplier ID: {old.get('supplier_id') or 'None'} -> {data.get('supplier_id') or 'None'}")
        if float(old["price"]) != float(data["price"]):
            changes.append(f"Price: P{float(old['price']):.2f} -> P{float(data['price']):.2f}")
        if int(old["quantity"]) != int(data["qty"]):
            changes.append(f"Qty: {old['quantity']} -> {data['qty']}")
        if int(old["threshold"]) != int(data["threshold"]):
            changes.append(f"Threshold: {old['threshold']} -> {data['threshold']}")

        diff_str = " | ".join(changes) if changes else "No field changes detected"
        log_action(
    f"[INVENTORY] Edited item: {data['name']} ({data['sku']}) | {diff_str}"
        )
    else:
        log_action(f"[INVENTORY] Edited item ({data['sku']}): {data['name']}")

    try:
        check_low_stock()
    except Exception:
        pass

    return jsonify({"success": True})


@inventory_bp.route("/api/inventory/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role", "").lower() != "admin":
        return jsonify({"error": "Forbidden"}), 403

    # ── Fetch item details BEFORE deleting so name is in the log ──
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT item_name, sku, category, price, quantity FROM inventory WHERE id=%s", (product_id,))
    item = cur.fetchone()

    cur2 = con.cursor()
    cur2.execute("DELETE FROM inventory WHERE id=%s", (product_id,))
    con.commit()
    create_notification(
        username=session.get('username'),
        notif_type='inventory',
        message=f"Item deleted: {item['item_name']}",
        link='/inventory'
    )
    cur.close()
    cur2.close()
    con.close()

    if item:
        log_action(
            f"[INVENTORY] Deleted item: {item['item_name']} | "
            f"SKU: {item['sku']} | Category: {item['category']} | "
            f"Price: ₱{float(item['price']):.2f} | Qty: {item['quantity']}"
        )
    else:
        log_action(f"[INVENTORY] Deleted item ID {product_id}")

    return jsonify({"success": True})


@inventory_bp.route("/api/inventory/barcode/<code>", methods=["GET"])
def lookup_barcode(code):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Normalize: strip leading zeros, then also try with leading zero padded to 13
    code = code.strip()
    variants = set()
    variants.add(code)
    variants.add(code.lstrip("0") or "0")        # strip leading zeros
    variants.add(code.zfill(13))                  # pad to 13 digits
    if len(code) == 12:
        variants.add("0" + code)                  # UPC-A → EAN-13
    if len(code) == 13 and code.startswith("0"):
        variants.add(code[1:])                    # EAN-13 → UPC-A

    placeholders = ", ".join(["%s"] * len(variants))
    query = f"""
        SELECT * FROM inventory 
        WHERE barcode IN ({placeholders}) OR sku IN ({placeholders})
        LIMIT 1
    """
    
    con = get_connection()
    cur = con.cursor(dictionary=True)
    params = list(variants) + list(variants)
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    con.close()
    
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id":        row["id"],
        "name":      row["item_name"],
        "sku":       row["sku"],
        "barcode":   row["barcode"],
        "category":  row["category"],
        "price":     float(row["price"]),
        "stock":     row["quantity"],
        "threshold": row["threshold"],
    })


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