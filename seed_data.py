"""Seed script: populates renzrap_db with realistic test data.
Idempotent — safe to run multiple times. Detects existing data and works around it."""
import mysql.connector
import hashlib, json, random
from datetime import datetime, timedelta
from config import DB_CONFIG

random.seed(42)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def receipt_id(idx):
    """Match sales.py: aaa000001..aaa999999, aab000000..aab999999, aac..."""
    if idx < 999999:
        group = 0
        digit = idx + 1
    else:
        adj = idx - 999999
        group = 1 + (adj // 1000000)
        digit = adj % 1000000
    l1 = chr(ord('a') + (group // 676) % 26)
    l2 = chr(ord('a') + (group // 26) % 26)
    l3 = chr(ord('a') + group % 26)
    return f"{l1}{l2}{l3}{digit:06d}"

def parse_receipt_index(rid):
    """Reverse of receipt_id()."""
    if len(rid) < 9:
        return None
    try:
        letters, digits = rid[:3], int(rid[3:])
        group = (ord(letters[0]) - ord('a')) * 676 + \
                (ord(letters[1]) - ord('a')) * 26 + \
                (ord(letters[2]) - ord('a'))
        if group == 0:
            return digits - 1  # idx 0 → aaa000001
        return 999999 + (group - 1) * 1000000 + digits
    except (ValueError, IndexError):
        return None

def make_sold_at(base_date, day_offset, tx_index, daily_count):
    d = base_date + timedelta(days=day_offset)
    total_slots = daily_count + 1
    slot = tx_index + 1
    hour = 8 + (slot * 10) // total_slots
    minute = random.randint(0, 59)
    return d.replace(hour=hour, minute=minute, second=random.randint(0, 59))

USERS = [
    ("Admin User", "admin", hash_password("password123"), "Admin",
     "admin@renzrap.test", "09171234567", "Main Office", "2024-01-01"),
    ("Manager", "manager", hash_password("manager1"), "Admin",
     "manager@renzrap.test", "09171234568", "Main Office", "2024-02-01"),
    ("Cashier Alice", "alice", hash_password("alice123"), "Employee",
     "alice@renzrap.test", "09171234569", "Branch 1", "2024-03-01"),
    ("Cashier Bob", "bob", hash_password("bob1234"), "Employee",
     "bob@renzrap.test", "09171234570", "Branch 1", "2024-03-15"),
    ("Inventory Clerk", "clerk", hash_password("clerk123"), "Employee",
     "clerk@renzrap.test", "09171234571", "Warehouse", "2024-04-01"),
    ("Admin Masi", "masi", hash_password("00000000"), "Admin",
     "masi@renzrap.test", "09171234572", "Main Office", "2024-01-01"),
]

SUPPLIERS = [
    ("MakinaPro Parts", "Engine Parts", "Active",
     "123 Makina St, Manila", "Juan dela Cruz", "0281234567", "orders@makinapro.ph", 3),
    ("EngineMaster Co.", "Engine Parts", "Active",
     "456 Makina Ave, QC", "Maria Santos", "0281234568", "sales@enginemaster.ph", 5),
    ("BrakeSafe Inc.", "Brakes", "Active",
     "789 Preno Rd, Makati", "Pedro Reyes", "0281234569", "info@brakesafe.ph", 2),
    ("StopWell Brakes", "Brakes", "Active",
     "321 Stop St, Mandaluyong", "Ana Cruz", "0281234570", "orders@stopwell.ph", 4),
    ("Electra Auto", "Electrical", "Active",
     "654 Kuryente Ave, Pasig", "Carlos Tan", "0281234571", "sales@electraauto.ph", 3),
    ("VoltStart Supplies", "Electrical", "Active",
     "987 Battery Rd, Caloocan", "Lisa Kim", "0281234572", "info@voltstart.ph", 2),
    ("ShockPro Suspension", "Suspension", "Active",
     "147 Spring St, Parañaque", "Ramon Diaz", "0281234573", "orders@shockpro.ph", 4),
    ("RideEasy Parts", "Suspension", "Active",
     "258 Gulong Ave, Las Piñas", "Elena Gomez", "0281234574", "sales@rideeasy.ph", 3),
    ("AutoBody Plus", "Body & Accessories", "Active",
     "369 Body St, Taguig", "Ben Torres", "0281234575", "info@autobody.ph", 5),
    ("PrimeAuto Parts", "Body & Accessories", "Active",
     "482 Access Rd, Valenzuela", "Diana Lim", "0281234576", "orders@primeauto.ph", 3),
]

INVENTORY = [
    ("Oil Filter", "OF-101", "4800010001011", "Engine Parts", 25, 250.00, 5, 0, 0),
    ("Air Filter", "AF-202", "4800010002022", "Engine Parts", 18, 380.00, 5, 0, 0),
    ("Spark Plug (Set of 4)", "SP-303", "4800010003033", "Engine Parts", 40, 180.00, 10, 0, 0),
    ("Timing Belt", "TB-404", "4800010004044", "Engine Parts", 0, 1200.00, 5, 0, 0),
    ("Engine Gasket Kit", "EG-505", "4800010005055", "Engine Parts", 8, 850.00, 5, 0, 0),
    ("Fuel Pump", "FP-606", "4800010006066", "Engine Parts", 3, 2500.00, 5, 0, 0),
    ("Radiator Cap", "RC-101", "4800020001011", "Engine Parts", 30, 120.00, 10, 1, 0),
    ("Water Pump", "WP-202", "4800020002022", "Engine Parts", 0, 1800.00, 5, 1, 0),
    ("Thermostat", "TH-303", "4800020003033", "Engine Parts", 15, 350.00, 5, 1, 0),
    ("Ignition Coil", "IC-404", "4800020004044", "Engine Parts", 12, 650.00, 5, 1, 0),
    ("Starter Motor", "SM-505", "4800020005055", "Engine Parts", 2, 3200.00, 5, 1, 0),
    ("Alternator", "AL-606", "4800020006066", "Engine Parts", 4, 4500.00, 3, 1, 0),
    ("Brake Pad Set (Front)", "BP-101", "4800030001011", "Brakes", 22, 1500.00, 5, 2, 0),
    ("Brake Disc Rotor", "BR-202", "4800030002022", "Brakes", 0, 1800.00, 5, 2, 0),
    ("Brake Caliper", "BC-303", "4800030003033", "Brakes", 6, 2200.00, 5, 2, 0),
    ("Brake Hose Line", "BL-404", "4800030004044", "Brakes", 14, 480.00, 5, 2, 0),
    ("Brake Fluid (1L)", "BF-505", "4800030005055", "Brakes", 20, 180.00, 10, 2, 0),
    ("Parking Brake Cable", "PB-606", "4800030006066", "Brakes", 9, 350.00, 5, 2, 0),
    ("Brake Master Cylinder", "MC-101", "4800040001011", "Brakes", 0, 2800.00, 3, 3, 0),
    ("Brake Shoe Set", "BS-202", "4800040002022", "Brakes", 10, 950.00, 5, 3, 0),
    ("Wheel Cylinder", "WC-303", "4800040003033", "Brakes", 7, 520.00, 5, 3, 0),
    ("ABS Sensor", "AB-404", "4800040004044", "Brakes", 5, 1200.00, 3, 3, 0),
    ("Brake Booster", "BB-505", "4800040005055", "Brakes", 0, 3500.00, 3, 3, 0),
    ("Brake Disc (Rear)", "BD-606", "4800040006066", "Brakes", 11, 1600.00, 5, 3, 0),
    ("Car Battery (1SM)", "CB-101", "4800050001011", "Electrical", 15, 3200.00, 5, 4, 0),
    ("Headlight Bulb H4", "HB-202", "4800050002022", "Electrical", 30, 250.00, 10, 4, 0),
    ("Tail Light Bulb", "TL-303", "4800050003033", "Electrical", 28, 120.00, 10, 4, 0),
    ("Turn Signal Relay", "TS-404", "4800050004044", "Electrical", 12, 180.00, 5, 4, 0),
    ("Fuse Set (Assorted)", "FS-505", "4800050005055", "Electrical", 20, 80.00, 10, 4, 0),
    ("Wiring Harness Kit", "WH-606", "4800050006066", "Electrical", 0, 1500.00, 3, 4, 0),
    ("Alternator Belt", "AB-101", "4800060001011", "Electrical", 18, 450.00, 5, 5, 0),
    ("Voltage Regulator", "VR-202", "4800060002022", "Electrical", 8, 380.00, 5, 5, 0),
    ("Ignition Switch", "IS-303", "4800060003033", "Electrical", 0, 550.00, 5, 5, 0),
    ("Door Lock Actuator", "DA-404", "4800060004044", "Electrical", 10, 750.00, 5, 5, 0),
    ("Electric Horn", "EH-505", "4800060005055", "Electrical", 14, 280.00, 5, 5, 0),
    ("Wiper Motor", "WM-606", "4800060006066", "Electrical", 6, 1200.00, 3, 5, 0),
    ("Shock Absorber (Front)", "SA-101", "4800070001011", "Suspension", 10, 2800.00, 5, 6, 0),
    ("Strut Mount", "SM-202", "4800070002022", "Suspension", 12, 650.00, 5, 6, 0),
    ("Coil Spring", "CS-303", "4800070003033", "Suspension", 0, 1800.00, 3, 6, 0),
    ("Lower Control Arm", "CA-404", "4800070004044", "Suspension", 5, 2200.00, 3, 6, 0),
    ("Ball Joint", "BJ-505", "4800070005055", "Suspension", 16, 480.00, 5, 6, 0),
    ("Sway Bar Link", "SB-606", "4800070006066", "Suspension", 9, 380.00, 5, 6, 0),
    ("Tie Rod End", "TR-101", "4800080001011", "Suspension", 20, 520.00, 5, 7, 0),
    ("Wheel Bearing", "WB-202", "4800080002022", "Suspension", 0, 850.00, 5, 7, 0),
    ("Steering Rack Boot", "SR-303", "4800080003033", "Suspension", 13, 280.00, 5, 7, 0),
    ("Stabilizer Link", "SL-404", "4800080004044", "Suspension", 11, 350.00, 5, 7, 0),
    ("Leaf Spring Bushing", "LS-505", "4800080005055", "Suspension", 7, 420.00, 5, 7, 0),
    ("Bushing Kit", "BK-606", "4800080006066", "Suspension", 4, 680.00, 3, 7, 0),
    ("Side Mirror (Left)", "SM-101", "4800090001011", "Body & Accessories", 8, 1200.00, 5, 8, 0),
    ("Door Handle (Ext)", "DH-202", "4800090002022", "Body & Accessories", 15, 250.00, 5, 8, 0),
    ("Window Regulator", "WR-303", "4800090003033", "Body & Accessories", 0, 900.00, 3, 8, 0),
    ("Hood Latch", "HL-404", "4800090004044", "Body & Accessories", 10, 180.00, 5, 8, 0),
    ("Front Bumper Cover", "BC-505", "4800090005055", "Body & Accessories", 2, 2500.00, 3, 8, 0),
    ("Chrome Grille", "CG-606", "4800090006066", "Body & Accessories", 5, 1500.00, 3, 8, 0),
    ("Floor Mat Set", "FM-101", "4800100001011", "Body & Accessories", 12, 850.00, 5, 9, 0),
    ("Seat Cover Set", "SC-202", "4800100002022", "Body & Accessories", 6, 1200.00, 5, 9, 0),
    ("Steering Wheel Cover", "SW-303", "4800100003033", "Body & Accessories", 20, 150.00, 10, 9, 0),
    ("Sun Visor Pair", "SV-404", "4800100004044", "Body & Accessories", 9, 380.00, 5, 9, 0),
    ("Mud Guard Set", "MG-505", "4800100005055", "Body & Accessories", 4, 450.00, 5, 9, 0),
    ("Wiper Blade (Pair)", "WB-606", "4800100006066", "Body & Accessories", 22, 280.00, 10, 9, 0),
]

def seed():
    con = mysql.connector.connect(**DB_CONFIG)
    cur = con.cursor(dictionary=True)

    print("Seeding renzrap_db …")

    # ─── Users (INSERT IGNORE) ─────────────────────────────
    print("  Adding users …")
    for u in USERS:
        name, username, pw, role, email, phone, addr, hired = u
        try:
            cur.execute(
                "INSERT INTO users (name, username, password, role, email, phone, address, date_hired) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (name, username, pw, role, email, phone, addr, hired)
            )
        except mysql.connector.IntegrityError:
            pass
    con.commit()

    # ─── Suppliers (check first, skip duplicates) ─────────
    print("  Adding suppliers …")
    supplier_ids = []
    for s in SUPPLIERS:
        cur.execute("SELECT id FROM suppliers WHERE name=%s", (s[0],))
        existing = cur.fetchone()
        if existing:
            supplier_ids.append(existing["id"])
        else:
            cur.execute(
                "INSERT INTO suppliers (name, category, status, address, contact, phone, email, delivery_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                s
            )
            supplier_ids.append(cur.lastrowid)
    con.commit()

    # ─── Inventory (check first, skip duplicates) ─────────
    print("  Adding inventory items …")
    item_map = {}
    for inv in INVENTORY:
        name, sku, barcode, cat, qty, price, thresh, sup_idx, inact = inv
        cur.execute("SELECT id FROM inventory WHERE sku=%s OR item_name=%s", (sku, name))
        existing = cur.fetchone()
        if existing:
            item_id = existing["id"]
        else:
            cur.execute(
                "INSERT INTO inventory (item_name, sku, barcode, category, quantity, price, threshold, supplier_id, inactive) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (name, sku, barcode, cat, qty, price, thresh, supplier_ids[sup_idx], inact)
            )
            item_id = cur.lastrowid
        item_map[name] = {"id": item_id, "sku": sku, "barcode": barcode,
                          "category": cat, "price": float(price), "threshold": int(thresh)}
    con.commit()

    # ─── Detect next receipt index ─────────────────────────
    cur.execute("SELECT id FROM sales ORDER BY id DESC LIMIT 1")
    last_row = cur.fetchone()
    receipt_idx = 0
    if last_row:
        idx = parse_receipt_index(last_row["id"])
        if idx is not None:
            receipt_idx = idx + 1
    print(f"  Starting sales receipt index at {receipt_idx} ({receipt_id(receipt_idx)})")

    # ─── Sales for 14 days (skip if sales already exist) ───
    cur.execute("SELECT COUNT(*) AS cnt FROM sales")
    if cur.fetchone()["cnt"] > 0:
        print("  Sales already exist — skipping generation")
        new_sales = 0
    else:
        print("  Generating sales for 14 days …")
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=14)
        all_items_list = list(item_map.values())
        local_receipt_idx = receipt_idx

        for day in range(14):
            is_weekend = (base_date + timedelta(days=day)).weekday() >= 5
            daily_tx = random.randint(8, 14) if not is_weekend else random.randint(4, 8)

            for tx in range(daily_tx):
                num_items = random.choices([1, 2, 3, 4, 5], weights=[20, 35, 25, 15, 5])[0]
                chosen = random.sample(all_items_list, min(num_items, len(all_items_list)))
                tx_items = []
                for it in chosen:
                    qty = random.choices([1, 1, 1, 2, 2, 3], weights=[30, 30, 20, 10, 5, 5])[0]
                    tx_items.append({
                        "id": it["id"],
                        "name": list(item_map.keys())[list(item_map.values()).index(it)],
                        "sku": it["sku"], "barcode": it["barcode"],
                        "category": it["category"],
                        "price": it["price"], "qty": qty, "threshold": it["threshold"],
                    })
                subtotal = sum(i["price"] * i["qty"] for i in tx_items)
                is_discounted = random.random() < 0.30
                discount = round(subtotal * 0.20, 2) if is_discounted else 0
                after_discount = subtotal - discount
                vat = round(after_discount - (after_discount / 1.12), 2)
                total = round(after_discount, 2)
                received = total
                if total > 0:
                    if total < 500:
                        received = ((total // 100) + 1) * 100 + random.choice([0, 0, 50])
                    elif total < 2000:
                        received = ((total // 500) + 1) * 500
                    else:
                        received = ((total // 1000) + 1) * 1000
                    if received < total:
                        received = total
                change = round(received - total, 2)
                sold_at = make_sold_at(base_date, day, tx, daily_tx)
                rid = receipt_id(local_receipt_idx)
                local_receipt_idx += 1
                cur.execute(
                    "INSERT INTO sales (id, items, subtotal, vat, total_price, amount_received, change_amount, sold_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (rid, json.dumps(tx_items), round(subtotal, 2), vat, total, round(received, 2), change, sold_at)
                )
        con.commit()
        new_sales = local_receipt_idx - receipt_idx
        print(f"    Inserted {new_sales} new sales transactions")

    # ─── Purchase Orders ─────────────────────────────────────
    print("  Adding purchase orders …")
    cur.execute("SELECT COUNT(*) AS cnt FROM purchase_orders")
    if cur.fetchone()["cnt"] == 0:
        po_data = [
            ("PO-2025-001", 0, "Draft", "Initial stock order — pending review", "admin"),
            ("PO-2025-002", 2, "Draft", "Brake parts order — awaiting approval", "manager"),
            ("PO-2025-003", 4, "Ordered", "Electrical supplies — sent to supplier", "admin"),
            ("PO-2025-004", 6, "Ordered", "Suspension parts — in transit", "manager"),
            ("PO-2025-005", 1, "Received", "Engine parts — fully received", "admin"),
            ("PO-2025-006", 8, "Received", "Body parts order — completed", "admin"),
        ]
        po_ids = []
        for po in po_data:
            po_num, sup_idx, status, notes, creator = po
            cur.execute(
                "INSERT INTO purchase_orders (po_number, supplier_id, supplier_name, status, notes, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (po_num, supplier_ids[sup_idx], SUPPLIERS[sup_idx][0], status, notes, creator)
            )
            po_ids.append(cur.lastrowid)

        order_items_data = [
            (po_ids[0], "Oil Filter", "OF-101", 10, 220.00),
            (po_ids[0], "Spark Plug (Set of 4)", "SP-303", 20, 150.00),
            (po_ids[0], "Air Filter", "AF-202", 10, 320.00),
            (po_ids[1], "Brake Pad Set (Front)", "BP-101", 8, 1200.00),
            (po_ids[1], "Brake Fluid (1L)", "BF-505", 15, 150.00),
            (po_ids[1], "Brake Hose Line", "BL-404", 10, 400.00),
            (po_ids[2], "Car Battery (1SM)", "CB-101", 10, 2800.00),
            (po_ids[2], "Headlight Bulb H4", "HB-202", 20, 200.00),
            (po_ids[2], "Fuse Set (Assorted)", "FS-505", 15, 60.00),
            (po_ids[3], "Shock Absorber (Front)", "SA-101", 6, 2400.00),
            (po_ids[3], "Ball Joint", "BJ-505", 10, 400.00),
            (po_ids[3], "Tie Rod End", "TR-101", 10, 420.00),
            (po_ids[4], "Water Pump", "WP-202", 5, 1500.00),
            (po_ids[4], "Ignition Coil", "IC-404", 8, 500.00),
            (po_ids[4], "Fuel Pump", "FP-606", 3, 2000.00),
            (po_ids[5], "Side Mirror (Left)", "SM-101", 5, 900.00),
            (po_ids[5], "Door Handle (Ext)", "DH-202", 10, 180.00),
            (po_ids[5], "Chrome Grille", "CG-606", 4, 1200.00),
        ]
        for oi in order_items_data:
            poi, name, sku, qty, uprice = oi
            inv_id = None
            for iname, info in item_map.items():
                if info["sku"] == sku:
                    inv_id = info["id"]
                    break
            cur.execute(
                "INSERT INTO order_items (po_id, item_id, item_name, sku, category, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s, (SELECT category FROM inventory WHERE id=%s), %s, %s)",
                (poi, inv_id, name, sku, inv_id, qty, uprice)
            )
        con.commit()
        print(f"    Inserted {len(po_data)} purchase orders with {len(order_items_data)} line items")
    else:
        print("    Purchase orders already exist — skipping")

    # ─── Reorder Orders ──────────────────────────────────────
    print("  Adding reorder orders …")
    cur.execute("SELECT COUNT(*) AS cnt FROM reorder_orders")
    if cur.fetchone()["cnt"] == 0:
        reorders = [
            (item_map["Fuel Pump"]["id"], "Fuel Pump", "FP-606", "Engine Parts",
             supplier_ids[0], "MakinaPro Parts", 5, "Pending"),
            (item_map["Starter Motor"]["id"], "Starter Motor", "SM-505", "Engine Parts",
             supplier_ids[1], "EngineMaster Co.", 3, "Pending"),
            (item_map["Brake Caliper"]["id"], "Brake Caliper", "BC-303", "Brakes",
             supplier_ids[2], "BrakeSafe Inc.", 4, "Received"),
            (item_map["Wiper Motor"]["id"], "Wiper Motor", "WM-606", "Electrical",
             supplier_ids[5], "VoltStart Supplies", 4, "Received"),
        ]
        for ro in reorders:
            iid, name, sku, cat, sid, sname, qty, status = ro
            cur.execute(
                "INSERT INTO reorder_orders (item_id, item_name, sku, category, supplier_id, supplier_name, qty_ordered, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (iid, name, sku, cat, sid, sname, qty, status)
            )
        con.commit()
        print(f"    Inserted {len(reorders)} reorder orders")
    else:
        print("    Reorder orders already exist — skipping")

    # ─── Notifications ───────────────────────────────────────
    print("  Adding notifications …")
    cur.execute("SELECT COUNT(*) AS cnt FROM notifications")
    if cur.fetchone()["cnt"] == 0:
        notifs = [
            ("admin", "sale", "Sale #aaa000001: 2x Oil Filter — ₱500.00", "/sales", 1),
            ("admin", "low_stock", "Low stock alert: Timing Belt (0 remaining)", "/inventory", 0),
            ("admin", "low_stock", "Low stock alert: Water Pump (0 remaining)", "/inventory", 0),
            ("admin", "low_stock", "Low stock alert: Fuel Pump (3 remaining)", "/inventory", 0),
            ("admin", "reorder", "Order received: Fuel Pump | Qty: 5 | Supplier: MakinaPro Parts", "/reorder", 1),
            ("admin", "password_reset", "Password reset requested by alice (Name: Cashier Alice). Code: 482951", "/admin/password-resets", 0),
            ("manager", "sale", "Sale #aaa000042: 1x Car Battery — ₱3,200.00", "/sales", 1),
            ("manager", "low_stock", "Low stock alert: Brake Disc Rotor (0 remaining)", "/inventory", 0),
            ("alice", "sale", "Sale #aaa000015: 3x Spark Plug — ₱540.00", "/sales", 1),
            ("bob", "sale", "Sale #aaa000078: 1x Shock Absorber — ₱2,800.00", "/sales", 0),
        ]
        for n in notifs:
            cur.execute(
                "INSERT INTO notifications (username, type, message, link, is_read) "
                "VALUES (%s, %s, %s, %s, %s)", n
            )
        con.commit()
        print(f"    Inserted {len(notifs)} notifications")
    else:
        print("    Notifications already exist — skipping")

    # ─── Reports (Z-Readings) ──────────────────────────────
    print("  Adding Z-readings …")
    cur.execute("SELECT COUNT(*) AS cnt FROM reports")
    if cur.fetchone()["cnt"] == 0:
        half_date = base_date + timedelta(days=7)
        now_date = base_date + timedelta(days=14)

        def compute_stats(until):
            cur.execute("""
                SELECT COALESCE(SUM(total_price),0) AS total_sales, COUNT(*) AS tx,
                       COALESCE(SUM(subtotal),0) AS sub, COALESCE(SUM(vat),0) AS vt,
                       COALESCE(SUM(amount_received),0) AS recv, COALESCE(SUM(change_amount),0) AS chg
                FROM sales WHERE sold_at >= %s AND sold_at < %s
            """, (base_date, until))
            r = cur.fetchone()
            ts = float(r["total_sales"]); tx = r["tx"]
            sub = float(r["sub"]); vt = float(r["vt"])
            recv = float(r["recv"]); chg = float(r["chg"])
            avg = round(ts / tx, 2) if tx else 0
            disc = round(sub - ts, 2)
            cur.execute("SELECT COUNT(*) AS cnt FROM sales WHERE sold_at >= %s AND sold_at < %s AND (subtotal - total_price) > 0.01",
                        (base_date, until))
            disc_tx = cur.fetchone()["cnt"]
            cur.execute("SELECT items FROM sales WHERE sold_at >= %s AND sold_at < %s", (base_date, until))
            total_items = 0
            for row in cur.fetchall():
                try:
                    total_items += len(json.loads(row["items"]))
                except:
                    pass
            return ts, tx, avg, vt, sub, disc, total_items, disc_tx, recv, chg

        ts1, tx1, avg1, vt1, sub1, disc1, ti1, dt1, recv1, chg1 = compute_stats(half_date)
        cur.execute(
            "INSERT INTO reports (reading_number, total_sales, transaction_count, avg_sale, vat_total, subtotal_total, "
            "discount_total, total_items_sold, discounted_transactions, total_received, total_change, start_date, end_date, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (1, round(ts1, 2), tx1, avg1, round(vt1, 2), round(sub1, 2),
             disc1, ti1, dt1, round(recv1, 2), round(chg1, 2),
             base_date, half_date, "admin")
        )

        ts2, tx2, avg2, vt2, sub2, disc2, ti2, dt2, recv2, chg2 = compute_stats(now_date)
        cur.execute(
            "INSERT INTO reports (reading_number, total_sales, transaction_count, avg_sale, vat_total, subtotal_total, "
            "discount_total, total_items_sold, discounted_transactions, total_received, total_change, start_date, end_date, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (2, round(ts2, 2), tx2, avg2, round(vt2, 2), round(sub2, 2),
             disc2, ti2, dt2, round(recv2, 2), round(chg2, 2),
             half_date, now_date, "admin")
        )
        con.commit()
        print("    Inserted 2 Z-readings")
    else:
        print("    Reports already exist — skipping")

    # ─── Activity Logs ──────────────────────────────────────
    print("  Adding activity logs …")
    cur.execute("SELECT COUNT(*) AS cnt FROM activity_logs")
    if cur.fetchone()["cnt"] == 0:
        logs = [
            ("admin", "Admin", "Logged in"),
            ("admin", "Admin", "Processed sale: 2x Oil Filter"),
            ("admin", "Admin", "Generated Z-Reading #1"),
            ("admin", "Admin", "Created purchase order PO-2025-001"),
            ("admin", "Admin", "Created purchase order PO-2025-003"),
            ("admin", "Admin", "Created purchase order PO-2025-005"),
            ("manager", "Admin", "Logged in"),
            ("manager", "Admin", "Created purchase order PO-2025-002"),
            ("manager", "Admin", "Created purchase order PO-2025-004"),
            ("manager", "Admin", "Marked PO-2025-004 as Ordered"),
            ("alice", "Employee", "Logged in"),
            ("alice", "Employee", "Processed sale: 3x Spark Plug"),
            ("alice", "Employee", "Processed sale: 1x Car Battery"),
            ("bob", "Employee", "Logged in"),
            ("bob", "Employee", "Processed sale: 1x Shock Absorber"),
            ("clerk", "Employee", "Logged in"),
            ("clerk", "Employee", "Updated inventory: Brake Disc Rotor — adjusted qty"),
            ("admin", "Admin", "Restored database from backup"),
            ("admin", "Admin", "Generated Z-Reading #2"),
            ("admin", "Admin", "Logged out"),
        ]
        for log in logs:
            cur.execute(
                "INSERT INTO activity_logs (username, role, action) VALUES (%s, %s, %s)", log
            )
        con.commit()
        print(f"    Inserted {len(logs)} activity log entries")
    else:
        print("    Activity logs already exist — skipping")

    # ─── Maintenance (backup) ──────────────────────────────
    print("  Adding maintenance backup …")
    cur.execute("SELECT COUNT(*) AS cnt FROM maintenance")
    if cur.fetchone()["cnt"] == 0:
        cur.execute("SELECT id, item_name, quantity, price FROM inventory LIMIT 10")
        snapshot_items = cur.fetchall()
        snapshot = json.dumps({"inventory": [dict(r) for r in snapshot_items], "note": "Sample backup snapshot"}, default=str)
        cur.execute(
            "INSERT INTO maintenance (snapshot, created_by) VALUES (%s, %s)",
            (snapshot, "admin")
        )
        con.commit()
        print("    Inserted 1 maintenance backup")
    else:
        print("    Maintenance backups already exist — skipping")

    cur.execute("SELECT COUNT(*) AS cnt FROM sales")
    total_sales = cur.fetchone()["cnt"]
    cur.close()
    con.close()

    print(f"\n  Done! Total sales in DB: {total_sales}")

if __name__ == "__main__":
    seed()
