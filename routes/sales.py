from flask import Blueprint, render_template, session, redirect, request, jsonify
from db import get_connection
from datetime import date, timedelta, datetime
import json, traceback
from routes.logger import log_action
from routes.notification_service import create_notification, check_low_stock

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
    cur.execute("SELECT id FROM sales ORDER BY CAST(SUBSTRING(id, 4) AS UNSIGNED) DESC LIMIT 1")
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
    amount_received = data.get("received", 0) or 0
    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    subtotal = sum(i["price"] * i["qty"] for i in items)
    discount = round(subtotal * 0.20, 2) if is_discounted else 0
    after_discount = subtotal - discount
    vat = round(after_discount - (after_discount / 1.12), 2)
    total = round(after_discount, 2)

    con = get_connection()
    cur = con.cursor(dictionary=True)
    receipt_id = generate_receipt_number(cur)

    cur = con.cursor()
    cur.execute(
        """INSERT INTO sales (id, items, subtotal, vat, total_price, amount_received, change_amount)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (receipt_id, json.dumps(items), subtotal, vat, total, float(amount_received), max(0, float(amount_received) - total))
    )
    for item in items:
        cur.execute(
            "UPDATE inventory SET quantity = quantity - %s WHERE id = %s",
            (item["qty"], item["id"])
        )

    con.commit()
    item_names = ", ".join([f"{i['qty']}x {i['name']}" for i in items])
    log_action(f"Processed sale: {item_names} ({receipt_id})")
    
    create_notification(
        username=session.get('username'),
        notif_type='sale',
        message=f'Sale #{receipt_id}: {item_names} — ₱{total:,.2f}',
        link='/sales'
    )
    cur.close()
    con.close()

    # Check for low stock after sale
    try:
        check_low_stock()
    except Exception:
        pass

    # Auto-print receipt to thermal printer
    try:
        ports = find_printer_ports()
        if ports:
            now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")
            change = max(0, float(amount_received) - total)
            rcpt_data = {
                "receipt_id": str(receipt_id),
                "date": now_str,
                "address": "123 Main St., City, Province",
                "items": items,
                "subtotal": f"₱{subtotal:,.2f}",
                "vat": f"₱{vat:,.2f}",
                "received": f"₱{float(amount_received):,.2f}",
                "change": f"₱{change:,.2f}",
                "grand_total": f"₱{total:,.2f}"
            }
            raw = escpos_receipt(rcpt_data).encode("latin-1", errors="replace")
            escpos_print(raw, ports)
    except Exception as e:
        print(f"[auto-print] Error: {e}")

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
        SELECT id, items, subtotal, vat, total_price, amount_received, change_amount, sold_at
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
            "received":   float(r["amount_received"] or 0),
            "change":     float(r["change_amount"] or 0),
            "created_at": r["sold_at"].isoformat() if r["sold_at"] else None,
        })
    return jsonify(result)


# ── Print receipt to Bluetooth/USB thermal printer ───────────────────────
def find_printer_ports():
    import serial, serial.tools.list_ports, subprocess, re
    ports = []
    found_coms = set()
    # 1. USB printer — enumerate VID 6868 PID 0200 dynamically
    try:
        ps = subprocess.run(["powershell", "-Command",
            "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USB\\VID_6868&PID_0200' -ErrorAction SilentlyContinue | "
            "Get-ItemProperty -Name SymbolicName -ErrorAction SilentlyContinue | "
            "Where-Object { $_.SymbolicName } | Select-Object -ExpandProperty SymbolicName"
        ], capture_output=True, text=True, timeout=5)
        for line in ps.stdout.strip().splitlines():
            line = line.strip()
            if line.startswith("\\??\\"):
                path = "\\\\.\\" + line[4:]
                ports.append(("usb", path))
    except:
        pass
    # 2. COM ports by description
    for p in serial.tools.list_ports.comports():
        if "PT210" in p.description or "PT-210" in p.description:
            ports.append(("com", p.device))
            found_coms.add(p.device)
    # 3. Bluetooth PT210A — match MAC from PnP to COM HWID
    try:
        ps = subprocess.run(["powershell", "-Command",
            "Get-CimInstance -ClassName Win32_PnPEntity | Where-Object { $_.Name -like '*PT210*' } | Select-Object -ExpandProperty DeviceID"
        ], capture_output=True, text=True, timeout=5)
        device_id = ps.stdout.strip()
        if device_id:
            mac_match = re.search(r'([0-9A-F]{12})', device_id.upper())
            if mac_match:
                mac = mac_match.group(1)
                for p in serial.tools.list_ports.comports():
                    if mac in p.hwid.upper() and p.device not in found_coms:
                        ports.append(("com", p.device))
                        found_coms.add(p.device)
    except:
        pass
    # 4. Direct COM8 Bluetooth fallback (known from pairing)
    if "COM8" not in found_coms:
        try:
            s = serial.Serial("COM8", baudrate=9600, timeout=2)
            s.close()
            ports.append(("com", "COM8"))
            found_coms.add("COM8")
        except:
            pass
    return ports

def escpos_print(raw_bytes, ports):
    import serial
    last_error = None
    for port_type, target in ports:
        try:
            if port_type == "com":
                with serial.Serial(target, baudrate=9600, timeout=5) as ser:
                    ser.write(raw_bytes)
                    ser.flush()
            elif port_type == "usb":
                import ctypes, ctypes.wintypes
                GENERIC_WRITE = 0x40000000
                OPEN_EXISTING = 3
                kernel32 = ctypes.windll.kernel32
                kernel32.CreateFileW.restype = ctypes.c_void_p
                kernel32.CreateFileW.argtypes = [
                    ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                    ctypes.c_void_p
                ]
                handle = kernel32.CreateFileW(
                    target, GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
                )
                if not handle or handle == ctypes.c_void_p(-1).value:
                    continue
                try:
                    written = ctypes.wintypes.DWORD(0)
                    buf = (ctypes.c_byte * len(raw_bytes)).from_buffer_copy(raw_bytes)
                    if not kernel32.WriteFile(handle, buf, len(raw_bytes), ctypes.byref(written), None):
                        continue
                    kernel32.FlushFileBuffers(handle)
                finally:
                    kernel32.CloseHandle(handle)
            return True
        except Exception as e:
            last_error = e
            continue
    raise last_error or OSError("No printer available")

def escpos_receipt(data):
    def sanitize(text):
        return str(text).replace("₱", "P").replace("—", "-")
    lines = []
    def center(text): lines.append(f"\x1b\x61\x01{sanitize(text)}\x0a")
    def left(text):   lines.append(f"\x1b\x61\x00{sanitize(text)}\x0a")
    def bold(text):   lines.append(f"\x1b\x45\x01{sanitize(text)}\x1b\x45\x00\x0a")
    def bold_center(text): lines.append(f"\x1b\x61\x01\x1b\x45\x01{sanitize(text)}\x1b\x45\x00\x0a")
    def sep():        lines.append("-" * 32 + "\x0a")
    def feed(n=1):    lines.append("\x0a" * n)

    bold_center("RENZ RAP AUTO SUPPLY")
    center("Auto Parts & Accessories")
    center(data.get("address", "123 Main St., City, Province"))
    center("Tel: (02) 1234-5678")
    feed()
    left(f"Receipt: {data.get('receipt_id', '-')}")
    left(f"Date: {data.get('date', '-')}")
    sep()
    left(f"{'Item':<13}{'Qty':>3} {'Price':>7}{'Total':>8}")
    sep()
    for item in data.get("items", []):
        name = sanitize(item.get("name", ""))[:13]
        qty = str(item.get("qty", 0))
        price = f"{float(item.get('price', 0)):.2f}"
        total = f"{float(item.get('qty', 0)) * float(item.get('price', 0)):.2f}"
        left(f"{name:<13}{qty:>3} {price:>7}{total:>8}")
    sep()
    left(f"{'Subtotal':<20}{sanitize(data.get('subtotal','')):>12}")
    left(f"{'VAT (12%)':<20}{sanitize(data.get('vat','')):>12}")
    left(f"{'Amount Received':<20}{sanitize(data.get('received','')):>12}")
    left(f"{'Change':<20}{sanitize(data.get('change','')):>12}")
    sep()
    bold(f"{'Grand Total':<20}{sanitize(data.get('grand_total','')):>12}")
    feed(2)
    center("Thank you for your purchase!")
    center("Mon-Sat 8AM-6PM")
    feed(3)
    lines.append("\x1d\x56\x00")
    return "".join(lines)

@sales_bp.route("/api/sales/print-receipt", methods=["POST"])
def print_receipt():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    ports = find_printer_ports()
    if not ports:
        print("[print-receipt] Printer not found")
        return jsonify({"error": "Printer not found"}), 404
    print(f"[print-receipt] Found {len(ports)} printer(s)")

    try:
        raw = escpos_receipt(data).encode("latin-1", errors="replace")
        print(f"[print-receipt] ESC/POS payload: {len(raw)} bytes")
        escpos_print(raw, ports)
        print("[print-receipt] Print successful")
        return jsonify({"success": True})
    except Exception as e:
        print(f"[print-receipt] Error: {e}")
        return jsonify({"error": str(e)}), 500