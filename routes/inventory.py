from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from routes.logger import log_action
from routes.notification_service import create_notification

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
            "qty":       r["quantity"],
            "threshold": r["threshold"],
            "inactive":  bool(r.get("inactive", False)),

        })
    return jsonify(products)


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
        """INSERT INTO inventory (item_name, sku, barcode, category, price, quantity, threshold)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data["name"], data["sku"], data.get("barcode", "").strip(),
         data["category"],
         data["price"], data["qty"], data["threshold"])
    )
    con.commit()
    try:
        create_notification(
            username=session.get('username'),
            notif_type='inventory',
            message=f"New item added: {data['name']} | Qty: {data['qty']} | ₱{float(data['price']):.2f}",
            link='/inventory'
        )
        print("✅ Notification created for", session.get('username'))
    except Exception as e:
        print("❌ Notification error:", e)
    new_id = cur.lastrowid
    cur.close()
    con.close()

    log_action(
        f"[INVENTORY] Added item: {data['name']} | "
        f"SKU: {data['sku']} | Category: {data['category']} | "
        f"Price: ₱{float(data['price']):.2f} | "
        f"Qty: {data['qty']} | Threshold: {data['threshold']}"
    )
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
       SET item_name=%s, sku=%s, barcode=%s, category=%s,
           price=%s, quantity=%s, threshold=%s, inactive=%s
       WHERE id=%s""",
    (data["name"], data["sku"], data.get("barcode", "").strip(),
     data["category"], data["price"], data["qty"],
     data["threshold"], int(data.get("inactive", False)),  # ← add this
     product_id)
)
    
    con.commit()
    create_notification(
        username=session.get('username'),
        notif_type='inventory',
        message=f"Item updated: {data['name']} | Qty: {data['qty']} | ₱{float(data['price']):.2f}",
        link='/inventory'
    )
    cur.close()
    cur2.close()
    con.close()

    # ── Build a diff log so the audit trail is meaningful ──
    if old:
        changes = []
        if old["item_name"] != data["name"]:
            changes.append(f"Name: '{old['item_name']}' → '{data['name']}'")
        if old["sku"] != data["sku"]:
            changes.append(f"SKU: '{old['sku']}' → '{data['sku']}'")
        if str(old.get("barcode", "") or "") != str(data.get("barcode", "") or ""):
            changes.append(f"Barcode: '{old.get('barcode','')}' → '{data.get('barcode','')}'")
        if old["category"] != data["category"]:
            changes.append(f"Category: '{old['category']}' → '{data['category']}'")
        if float(old["price"]) != float(data["price"]):
            changes.append(f"Price: ₱{float(old['price']):.2f} → ₱{float(data['price']):.2f}")
        if int(old["quantity"]) != int(data["qty"]):
            changes.append(f"Qty: {old['quantity']} → {data['qty']}")
        if int(old["threshold"]) != int(data["threshold"]):
            changes.append(f"Threshold: {old['threshold']} → {data['threshold']}")

        diff_str = " | ".join(changes) if changes else "No field changes detected"
        log_action(
    f"[INVENTORY] Edited item: {data['name']} ({data['sku']}) | {diff_str}"
        )
    else:
        log_action(f"[INVENTORY] Edited item ({data['sku']}): {data['name']}")


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