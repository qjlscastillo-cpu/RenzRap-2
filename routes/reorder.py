from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from routes.logger import log_action
from routes.notification_service import create_notification

reorder_bp = Blueprint("reorder", __name__)


@reorder_bp.route("/reorder")
def reorder():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("reorder.html", active_page="reorder", role=session.get("role"))


@reorder_bp.route("/api/reorder-items", methods=["GET"])
def get_reorder_items():
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
        qty = int(r["quantity"])
        threshold = int(r["threshold"])
        if qty <= 0 or qty <= threshold:
            products.append({
                "id":        r["id"],
                "name":      r["item_name"],
                "sku":       r["sku"],
                "category":  r["category"],
                "price":     float(r["price"]),
                "qty":       qty,
                "threshold": threshold,
                "status":    "Out of Stock" if qty <= 0 else "Low Stock"
            })
    return jsonify(products)


@reorder_bp.route("/api/reorder-request", methods=["POST"])
def reorder_request():
    """
    Save a new reorder to the `reorder_orders` table.

    Run once in MySQL to create the table:

    CREATE TABLE reorder_orders (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        item_id       INT NOT NULL,
        item_name     VARCHAR(255) NOT NULL,
        sku           VARCHAR(100),
        category      VARCHAR(100),
        supplier_id   INT NOT NULL,
        supplier_name VARCHAR(255),
        qty_ordered   INT NOT NULL DEFAULT 1,
        status        ENUM('Pending','Received') DEFAULT 'Pending',
        date_requested DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data        = request.get_json() or {}
    item_id     = data.get("id")
    supplier_id = data.get("supplier_id")

    if not item_id:
        return jsonify({"error": "Missing item id"}), 400
    if not supplier_id:
        return jsonify({"error": "Missing supplier"}), 400

    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        qty = 1

    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("SELECT item_name, sku, category, quantity FROM inventory WHERE id=%s", (item_id,))
        item = cur.fetchone()
        if not item:
            cur.close(); con.close()
            return jsonify({"error": "Item not found"}), 404

        cur.execute("SELECT name FROM suppliers WHERE id=%s", (supplier_id,))
        supplier = cur.fetchone()
        if not supplier:
            cur.close(); con.close()
            return jsonify({"error": "Supplier not found"}), 404

        cur2 = con.cursor()
        cur2.execute("""
            INSERT INTO reorder_orders
                (item_id, item_name, sku, category, supplier_id, supplier_name, qty_ordered)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            item_id,
            item["item_name"],
            item["sku"],
            item["category"],
            supplier_id,
            supplier["name"],
            qty
        ))
        con.commit()
        create_notification(
            username=session.get('username'),
            notif_type='reorder',
            message=f"Reorder placed: {item['item_name']} | Qty: {qty} | Supplier: {supplier['name']}",
            link='/reorder'
        )
        cur.close()
        cur2.close()
        con.close()

        log_action(
            f"[REORDER] Order placed: {item['item_name']} | "
            f"SKU: {item['sku']} | Category: {item['category']} | "
            f"Qty: {qty} | Supplier: {supplier['name']}"
        )
        return jsonify({"success": True}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reorder_bp.route("/api/reorder-requests", methods=["GET"])
def get_reorder_requests():
    """Returns all PENDING orders from the reorder_orders table."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT
                id,
                item_id,
                item_name     AS name,
                sku,
                category,
                supplier_name,
                qty_ordered,
                status,
                DATE_FORMAT(date_requested, '%Y-%m-%d') AS date_requested
            FROM reorder_orders
            WHERE status = 'Pending'
            ORDER BY date_requested DESC
        """)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reorder_bp.route("/api/orders/<int:order_id>/received", methods=["PUT"])
def mark_received(order_id):
    """
    Mark an order as Received and add qty back to inventory.

    Run once in MySQL if you haven't already:
        ALTER TABLE reorder_orders ADD COLUMN date_received DATETIME DEFAULT NULL;
    """
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        con = get_connection()

        # ── 1. Fetch the pending order ──────────────────
        cur = con.cursor(dictionary=True)
        cur.execute(
            """SELECT item_id, item_name, supplier_name, qty_ordered
               FROM reorder_orders
               WHERE id = %s AND status = 'Pending'""",
            (order_id,)
        )
        order = cur.fetchone()
        cur.close()

        if not order:
            con.close()
            return jsonify({"error": "Order not found or already received"}), 404

        # ── 2. Run both UPDATEs on a single cursor ──────
        cur2 = con.cursor()

        cur2.execute(
            "UPDATE reorder_orders SET status = 'Received', date_received = NOW() WHERE id = %s",
            (order_id,)
        )
        cur2.execute(
            "UPDATE inventory SET quantity = quantity + %s WHERE id = %s",
            (order["qty_ordered"], order["item_id"])
        )

        con.commit()
        con.commit()
        create_notification(
            username=session.get('username'),
            notif_type='reorder',
            message=f"Order received: {order['item_name']} | Qty: {order['qty_ordered']} | Supplier: {order['supplier_name']}",
            link='/reorder'
        )
        cur2.close()
        cur2.close()
        con.close()

        log_action(
            f"[REORDER] Order received: {order['item_name']} | "
            f"Supplier: {order['supplier_name']} | "
            f"Qty added to inventory: {order['qty_ordered']}"
        )
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reorder_bp.route("/api/reorder-history", methods=["GET"])
def get_reorder_history():
    """Returns all Received rows from reorder_orders, newest first."""
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT
                id,
                item_id,
                item_name     AS name,
                sku,
                category,
                supplier_name,
                qty_ordered,
                DATE_FORMAT(date_requested, '%Y-%m-%d') AS date_requested,
                DATE_FORMAT(date_received,  '%Y-%m-%d') AS date_received
            FROM reorder_orders
            WHERE status = 'Received'
            ORDER BY date_received DESC
        """)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500