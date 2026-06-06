from flask import Blueprint, jsonify, request, session, redirect, render_template
from db import get_connection
from routes.logger import log_action

purchase_bp = Blueprint('purchase_orders', __name__)


@purchase_bp.route('/purchase-orders')
def purchase_orders_page():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('purchase_orders.html', active_page='purchase_orders', role=session.get('role'))


@purchase_bp.route('/api/purchase-orders/items')
def get_po_items():
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT id, item_name AS name, sku, category, quantity AS qty,
                   price, threshold, inactive, supplier_id
            FROM inventory
            WHERE inactive IS NULL OR inactive = 0
            ORDER BY quantity ASC, item_name ASC
        """)
        rows = cur.fetchall()
        cur.close()
        con.close()
        for r in rows:
            q = r.get('qty', 0) or 0
            t = r.get('threshold', 0) or 0
            if r.get('inactive'):
                r['status'] = 'Inactive'
            elif q <= 0:
                r['status'] = 'Out of Stock'
            elif q <= t:
                r['status'] = 'Low Stock'
            else:
                r['status'] = 'In Stock'
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders/auto-draft', methods=['GET'])
def auto_draft_preview():
    """Analyse inventory and suggest draft POs grouped by supplier."""
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("""
            SELECT i.id, i.item_name AS name, i.sku, i.category, i.quantity AS qty,
                   i.price, i.threshold, i.supplier_id,
                   s.id AS s_id, s.name AS s_name, s.category AS s_category,
                   COALESCE(s.delivery_time, 0) AS delivery_time
            FROM inventory i
            LEFT JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.inactive = 0
              AND (i.quantity <= 0 OR (i.threshold IS NOT NULL AND i.quantity <= i.threshold))
            ORDER BY i.item_name ASC
        """)
        rows = cur.fetchall()
        cur.close()
        con.close()

        suggestions = []
        for item in rows:
            q = item['qty'] or 0
            t = item['threshold'] or 1
            dt = item['delivery_time'] or 0
            multiplier = max(dt, 2)
            suggested_qty = max(t * multiplier - q, 1)

            suggestions.append({
                'id': item['id'],
                'name': item['name'],
                'sku': item['sku'] or '',
                'category': item['category'] or '',
                'qty': q,
                'price': float(item['price']) if item['price'] else 0,
                'threshold': t,
                'supplier_id': item['supplier_id'],
                'suggested_qty': suggested_qty,
                'matched_suppliers': [{
                    'id': item['s_id'] if item['s_id'] else 0,
                    'name': item['s_name'] if item['s_name'] else 'No Supplier',
                    'category': item['s_category'] or ''
                }]
            })

        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders/auto-draft', methods=['POST'])
def create_auto_drafts():
    """Create Draft POs from auto-draft preview, grouped by supplier."""
    try:
        d = request.json
        groups = d.get('groups', [])
        created_by = session.get('username', 'unknown')

        if not groups:
            return jsonify({'error': 'No groups provided'}), 400

        con = get_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM purchase_orders")
        next_id = (cur.fetchone()['max_id'] or 0) + 1

        created = []
        for grp in groups:
            supplier_id = grp.get('supplier_id')
            supplier_name = grp.get('supplier_name', '')
            items = grp.get('items', [])
            if not items:
                continue

            po_number = f"PO-{next_id:04d}"
            next_id += 1

            cur.execute("""
                INSERT INTO purchase_orders (po_number, supplier_id, supplier_name, status, notes, created_by)
                VALUES (%s, %s, %s, 'Draft', %s, %s)
            """, (po_number, supplier_id, supplier_name,
                  f"Auto-generated reorder draft", created_by))
            po_id = cur.lastrowid

            for item in items:
                cur.execute("""
                    INSERT INTO order_items (po_id, item_id, item_name, sku, category, quantity, unit_price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    po_id,
                    item.get('item_id'),
                    item.get('item_name'),
                    item.get('sku', ''),
                    item.get('category', ''),
                    item.get('quantity', 1),
                    item.get('unit_price', 0)
                ))

            created.append({'po_id': po_id, 'po_number': po_number, 'supplier_name': supplier_name})
            item_names = ', '.join(i.get('item_name', '') for i in items)
            log_action(f"Auto-draft PO {po_number} | Supplier: {supplier_name} | Items: {item_names}")

        con.commit()
        cur.close()
        con.close()

        return jsonify({'created': created, 'count': len(created)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders', methods=['GET'])
def list_purchase_orders():
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("""
            SELECT po.*,
                   COALESCE((SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.po_id = po.id), 0) AS total_items
            FROM purchase_orders po
            ORDER BY po.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders/<int:po_id>', methods=['GET'])
def get_purchase_order(po_id):
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM purchase_orders WHERE id = %s", (po_id,))
        po = cur.fetchone()
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404
        cur.execute("SELECT * FROM order_items WHERE po_id = %s", (po_id,))
        po['items'] = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(po)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders', methods=['POST'])
def create_purchase_order():
    try:
        d = request.json
        supplier_id = d.get('supplier_id')
        supplier_name = d.get('supplier_name', '')
        notes = d.get('notes', '')
        items = d.get('items', [])
        created_by = session.get('username', 'unknown')

        if not items:
            return jsonify({'error': 'At least one item is required'}), 400

        con = get_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM purchase_orders")
        next_id = cur.fetchone()['next_id']
        po_number = f"PO-{next_id:04d}"

        cur.execute("""
            INSERT INTO purchase_orders (po_number, supplier_id, supplier_name, status, notes, created_by)
            VALUES (%s, %s, %s, 'Ordered', %s, %s)
        """, (po_number, supplier_id, supplier_name, notes, created_by))
        po_id = cur.lastrowid

        for item in items:
            cur.execute("""
                INSERT INTO order_items (po_id, item_id, item_name, sku, category, quantity, unit_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                po_id,
                item.get('item_id'),
                item.get('item_name'),
                item.get('sku', ''),
                item.get('category', ''),
                item.get('quantity', 1),
                item.get('unit_price', 0)
            ))

        con.commit()
        cur.close()
        con.close()

        item_names = ', '.join(i.get('item_name', '') for i in items)
        log_action(f"Created purchase order {po_number} | Supplier: {supplier_name} | Items: {item_names}")

        return jsonify({'id': po_id, 'po_number': po_number}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders/<int:po_id>/status', methods=['PUT'])
def update_po_status(po_id):
    try:
        d = request.json
        new_status = d.get('status')
        if new_status not in ('Draft', 'Ordered', 'Received', 'Cancelled'):
            return jsonify({'error': 'Invalid status'}), 400

        con = get_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("SELECT * FROM purchase_orders WHERE id = %s", (po_id,))
        po = cur.fetchone()
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404

        if new_status == 'Received':
            cur.execute("SELECT * FROM order_items WHERE po_id = %s", (po_id,))
            items = cur.fetchall()
            for item in items:
                cur.execute("""
                    UPDATE inventory SET quantity = quantity + %s
                    WHERE id = %s
                """, (item['quantity'], item['item_id']))

        cur.execute("UPDATE purchase_orders SET status = %s WHERE id = %s", (new_status, po_id))
        con.commit()
        cur.close()
        con.close()

        log_action(f"Purchase order {po['po_number']} status changed to {new_status}")
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@purchase_bp.route('/api/purchase-orders/<int:po_id>', methods=['DELETE'])
def delete_purchase_order(po_id):
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM purchase_orders WHERE id = %s", (po_id,))
        po = cur.fetchone()
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404
        if po['status'] not in ('Draft', 'Cancelled'):
            return jsonify({'error': 'Only Draft or Cancelled orders can be deleted'}), 400

        cur.execute("DELETE FROM order_items WHERE po_id = %s", (po_id,))
        cur.execute("DELETE FROM purchase_orders WHERE id = %s", (po_id,))
        con.commit()
        cur.close()
        con.close()
        log_action(f"Deleted purchase order {po['po_number']}")
        return jsonify({'deleted': po_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
