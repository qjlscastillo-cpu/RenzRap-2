from flask import Blueprint, jsonify, request, session, redirect, render_template
from db import get_connection
from routes.security import log_action

supplier_bp = Blueprint('supplier', __name__)


# ── Page Route ─────────────────────────────────────────────────────────────
@supplier_bp.route('/supplier')
def supplier():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template('supplier.html', active_page='supplier', role=session.get('role'))


# ── GET all suppliers ──────────────────────────────────────────────────────
@supplier_bp.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM suppliers ORDER BY name ASC")
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── POST add supplier ──────────────────────────────────────────────────────
@supplier_bp.route('/api/suppliers', methods=['POST'])
def add_supplier():
    try:
        d = request.json
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO suppliers (name, category, status, address, contact, phone, email, inactive)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            d.get('name'),
            d.get('category'),
            d.get('status', 'Active'),
            d.get('address', ''),
            d.get('contact', ''),
            d.get('phone', ''),
            d.get('email', ''),
            d.get('inactive', False)
        ))
        con.commit()
        new_id = cur.lastrowid
        cur.close()
        con.close()
        log_action(
            f"Added supplier: {d.get('name')} | "
            f"Category: {d.get('category')} | Status: {d.get('status', 'Active')} | "
            f"Address: {d.get('address', '')} | Contact: {d.get('contact', '')} | "
            f"Phone: {d.get('phone', '')} | Email: {d.get('email', '')}"
        )
        return jsonify({'id': new_id, **d}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PUT update supplier ────────────────────────────────────────────────────
@supplier_bp.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    try:
        d = request.json
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM suppliers WHERE id=%s", (supplier_id,))
        old = cur.fetchone()
        cur2 = con.cursor()
        cur2.execute("""
            UPDATE suppliers
            SET name=%s, category=%s, status=%s,
                address=%s, contact=%s, phone=%s, email=%s, inactive=%s
            WHERE id=%s
        """, (
            d.get('name'),
            d.get('category'),
            d.get('status', 'Active'),
            d.get('address', ''),
            d.get('contact', ''),
            d.get('phone', ''),
            d.get('email', ''),
            d.get('inactive', False),
            supplier_id
        ))
        con.commit()
        cur.close()
        cur2.close()
        con.close()

        if old:
            changes = []
            if old.get('name') != d.get('name'):
                changes.append(f"Name: '{old.get('name')}' → '{d.get('name')}'")
            if old.get('category') != d.get('category'):
                changes.append(f"Category: '{old.get('category')}' → '{d.get('category')}'")
            if old.get('status') != d.get('status'):
                changes.append(f"Status: '{old.get('status')}' → '{d.get('status')}'")
            if old.get('address') != d.get('address'):
                changes.append(f"Address: '{old.get('address')}' → '{d.get('address')}'")
            if old.get('contact') != d.get('contact'):
                changes.append(f"Contact: '{old.get('contact')}' → '{d.get('contact')}'")
            if old.get('phone') != d.get('phone'):
                changes.append(f"Phone: '{old.get('phone')}' → '{d.get('phone')}'")
            if old.get('email') != d.get('email'):
                changes.append(f"Email: '{old.get('email')}' → '{d.get('email')}'")
            diff_str = ' | '.join(changes) if changes else 'No field changes detected'
            log_action(f"Edited supplier: {d.get('name')} | {diff_str}")
        else:
            log_action(f"Edited supplier: {d.get('name')}")
        return jsonify({'id': supplier_id, **d})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── DELETE supplier ────────────────────────────────────────────────────────
@supplier_bp.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    try:
        con = get_connection()
        cur = con.cursor(dictionary=True)
        cur.execute("SELECT * FROM suppliers WHERE id=%s", (supplier_id,))
        row = cur.fetchone()
        cur2 = con.cursor()
        cur2.execute("DELETE FROM suppliers WHERE id=%s", (supplier_id,))
        con.commit()
        cur.close()
        cur2.close()
        con.close()
        if row:
            log_action(
                f"Deleted supplier: {row.get('name')} | "
                f"Category: {row.get('category')} | Status: {row.get('status')} | "
                f"Address: {row.get('address')} | Contact: {row.get('contact')} | "
                f"Phone: {row.get('phone')} | Email: {row.get('email')}"
            )
        else:
            log_action(f"Deleted supplier ID {supplier_id}")
        return jsonify({'deleted': supplier_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500