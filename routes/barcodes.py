import io, random, string
from flask import Blueprint, render_template, session, redirect, request, jsonify, send_file
from db import get_connection
from routes.logger import log_action

barcodes_bp = Blueprint("barcodes", __name__)

def ean8_checksum(digits7):
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits7))
    return str((10 - (total % 10)) % 10)

@barcodes_bp.route("/barcodes")
def barcodes_page():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("barcodes.html", active_page="barcodes", role=session.get("role"))

@barcodes_bp.route("/api/barcodes/products")
def list_products():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    con = get_connection()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id, item_name, sku, barcode, price, quantity FROM inventory ORDER BY item_name")
    rows = cur.fetchall()
    cur.close(); con.close()
    return jsonify([{
        "id": r["id"], "name": r["item_name"], "sku": r["sku"],
        "barcode": r["barcode"] or "", "has_barcode": bool(r["barcode"]),
        "price": float(r["price"]), "qty": r["quantity"]
    } for r in rows])

@barcodes_bp.route("/api/barcodes/generate", methods=["POST"])
def generate_barcode():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    product_id = request.json.get("product_id")
    if not product_id:
        return jsonify({"error": "Missing product_id"}), 400

    con = get_connection()
    cur = con.cursor()
    code = None
    for _ in range(100):
        digits7 = "".join(random.choices(string.digits, k=7))
        check = ean8_checksum(digits7)
        candidate = digits7 + check
        cur.execute("SELECT COUNT(*) FROM inventory WHERE barcode = %s", (candidate,))
        if cur.fetchone()[0] == 0:
            code = candidate
            break
    if not code:
        cur.close(); con.close()
        return jsonify({"error": "Could not generate unique barcode"}), 500

    cur.execute("UPDATE inventory SET barcode = %s WHERE id = %s", (code, product_id))
    con.commit()
    cur.close(); con.close()

    log_action(f"[BARCODE] Generated barcode {code} for product ID {product_id}")
    return jsonify({"barcode": code})

@barcodes_bp.route("/api/barcodes/<barcode>/image")
def barcode_image(barcode):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        import barcode as pybarcode
        from barcode.writer import SVGWriter
        rv = io.BytesIO()
        code = pybarcode.get("ean8", barcode, writer=SVGWriter())
        code.write(rv)
        rv.seek(0)
        return send_file(rv, mimetype="image/svg+xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
