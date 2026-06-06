import mysql.connector
import random

conn = mysql.connector.connect(host='localhost', user='root', password='jolohotdog789', database='renzrap_db')
cur = conn.cursor()

print("Clearing old data...")
cur.execute("DELETE FROM order_items")
cur.execute("DELETE FROM purchase_orders")
cur.execute("DELETE FROM inventory")
cur.execute("DELETE FROM suppliers")
conn.commit()

suppliers = [
    # Original 10
    ("Toyota Parts Depot",      "Engine Parts",   "Active", "Caloocan City, Metro Manila",    "Santos, Michael",     "09171234567", "michael.santos@toyotadepot.ph",       5),
    ("Mitsubishi Auto Supply",   "Engine Parts",   "Active", "Makati City, Metro Manila",       "Reyes, Maria",        "09182345678", "maria.reyes@mitsubishi-autosupply.ph", 7),
    ("Brake Masters Inc.",       "Brake System",   "Active", "Quezon City, Metro Manila",       "Dela Cruz, Juan",     "09193456789", "juan.delacruz@brakemasters.ph",        3),
    ("Filter Pro Trading",       "Fluids & Oils",  "Active", "Pasig City, Metro Manila",        "Garcia, Ana",         "09204567890", "ana.garcia@filterpro.ph",              4),
    ("Electrical Motorshop",     "Electrical",     "Active", "Mandaluyong City, Metro Manila",   "Villanueva, Jose",    "09215678901", "jose.villanueva@electromotorshop.ph",   6),
    ("Suspension Kingdom",       "Suspension",     "Active", "Marikina City, Metro Manila",     "Fernandez, Carlos",   "09226789012", "carlos.fernandez@suspensionkingdom.ph", 5),
    ("Body Parts Hub",           "Body Parts",     "Active", "Valenzuela City, Metro Manila",    "Torres, Luis",        "09237890123", "luis.torres@bodypartshub.ph",          8),
    ("Piston & Rings Co.",       "Engine Parts",   "Active", "Las Pinas City, Metro Manila",     "Ramirez, Pedro",      "09248901234", "pedro.ramirez@pistonrings.ph",         4),
    ("Cooling & AC Supply",      "Electrical",     "Active", "Paranaque City, Metro Manila",     "Hernandez, Roberto",  "09259012345", "roberto.hernandez@coolingac.ph",       6),
    ("Universal Auto Parts",     "Others",         "Active", "Taguig City, Metro Manila",        "Mendoza, Karen",      "09260123456", "karen.mendoza@universalautoparts.ph",  3),

    # 10 New suppliers
    ("Diesel Parts Specialist",  "Engine Parts",   "Active", "Manila City, Metro Manila",        "Cruz, Antonio",       "09271234567", "antonio.cruz@dieselparts.ph",          5),
    ("Camshaft Trading",         "Engine Parts",   "Active", "Pasay City, Metro Manila",         "Lim, Benson",         "09281234567", "benson.lim@camshaftrading.ph",         4),
    ("Stopping Power Inc.",      "Brake System",   "Active", "San Juan City, Metro Manila",      "Tan, Michelle",       "09291234567", "michelle.tan@stoppingpower.ph",        3),
    ("Lubricants Depot",         "Fluids & Oils",  "Active", "Muntinlupa City, Metro Manila",    "Rivera, Carlos",      "09301234567", "carlos.rivera@lubricantsdepot.ph",     4),
    ("Wiring Harness Supply",    "Electrical",     "Active", "Navotas City, Metro Manila",       "Domingo, Francis",    "09311234567", "francis.domingo@wiringharness.ph",     6),
    ("Chassis Parts Co.",        "Suspension",     "Active", "Malabon City, Metro Manila",       "Soriano, Miguel",     "09321234567", "miguel.soriano@chassisparts.ph",       5),
    ("Fender & Panel Shop",      "Body Parts",     "Active", "San Mateo, Rizal",                 "Alcantara, Rosa",     "09331234567", "rosa.alcantara@fenderpanel.ph",        7),
    ("Fasteners & Hardware",     "Others",         "Active", "Cainta, Rizal",                    "Villamor, Dennis",    "09341234567", "dennis.villamor@fastenershardware.ph", 3),
    ("General Auto Supply",      "Others",         "Active", "Antipolo City, Rizal",             "Magsaysay, Philip",   "09351234567", "philip.magsaysay@generalauto.ph",      4),
    ("Transmission Parts Co.",   "Engine Parts",   "Active", "Sta. Rosa, Laguna",                "Mercado, Gregorio",   "09361234567", "gregorio.mercado@transmissionparts.ph",6),
]

print("Inserting 20 suppliers...")
for s in suppliers:
    cur.execute("""
        INSERT INTO suppliers (name, category, status, address, contact, phone, email, delivery_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, s)
conn.commit()
print(f"  {len(suppliers)} suppliers inserted.")

products = [
    # ── Fluids & Oils (10) ──
    ("Oil Filter",              "OFL-001", "Fluids & Oils",   150,  5,  "Filter Pro Trading"),
    ("Air Filter",              "AFL-002", "Fluids & Oils",   250,  5,  "Filter Pro Trading"),
    ("Engine Oil 5W-30 4L",     "OIL-001", "Fluids & Oils",  1800, 20,  "Filter Pro Trading"),
    ("Engine Oil 10W-40 4L",    "OIL-002", "Fluids & Oils",  1600, 20,  "Filter Pro Trading"),
    ("Transmission Fluid 4L",   "OIL-003", "Fluids & Oils",  2400, 10,  "Filter Pro Trading"),
    ("Coolant 1L",              "OIL-004", "Fluids & Oils",   400, 20,  "Filter Pro Trading"),
    ("Power Steering Fluid 1L", "OIL-005", "Fluids & Oils",   350, 15,  "Lubricants Depot"),
    ("Gear Oil 4L",             "OIL-006", "Fluids & Oils",  2200, 10,  "Lubricants Depot"),
    ("Diesel Oil 4L",           "OIL-007", "Fluids & Oils",  2000, 15,  "Lubricants Depot"),
    ("Hydraulic Fluid 1L",      "OIL-008", "Fluids & Oils",   500, 12,  "Lubricants Depot"),

    # ── Brake System (10) ──
    ("Brake Pad Set",           "BRK-001", "Brake System",   1200, 10,  "Brake Masters Inc."),
    ("Brake Disc Rotor",        "BRK-002", "Brake System",   2500,  8,  "Brake Masters Inc."),
    ("Brake Caliper",           "BRK-003", "Brake System",   3500,  6,  "Brake Masters Inc."),
    ("Brake Master Cylinder",   "BRK-004", "Brake System",   2800,  5,  "Brake Masters Inc."),
    ("Brake Fluid 1L",          "BRK-005", "Brake System",    350, 15,  "Brake Masters Inc."),
    ("Brake Shoe Set",          "BRK-006", "Brake System",   1500,  8,  "Stopping Power Inc."),
    ("Brake Drum",              "BRK-007", "Brake System",   2200,  6,  "Stopping Power Inc."),
    ("Parking Brake Cable",     "BRK-008", "Brake System",    800, 10,  "Stopping Power Inc."),
    ("ABS Sensor",              "BRK-009", "Brake System",   1800,  5,  "Stopping Power Inc."),
    ("Brake Booster",           "BRK-010", "Brake System",   4500,  4,  "Brake Masters Inc."),

    # ── Electrical (15) ──
    ("Spark Plug Set",          "ELC-001", "Electrical",      800, 15,  "Electrical Motorshop"),
    ("Battery 12V 2SM",         "ELC-002", "Electrical",     3500,  8,  "Electrical Motorshop"),
    ("Alternator Assembly",     "ELC-003", "Electrical",     5500,  4,  "Electrical Motorshop"),
    ("Starter Motor",           "ELC-004", "Electrical",     4800,  4,  "Electrical Motorshop"),
    ("Ignition Coil",           "ELC-005", "Electrical",     2200,  6,  "Electrical Motorshop"),
    ("A/C Compressor",          "ELC-006", "Electrical",     8500,  3,  "Cooling & AC Supply"),
    ("Radiator Assembly",       "ELC-007", "Electrical",     6500,  4,  "Cooling & AC Supply"),
    ("Condenser Fan Motor",     "ELC-008", "Electrical",     3500,  5,  "Cooling & AC Supply"),
    ("Blower Motor",            "ELC-009", "Electrical",     4200,  4,  "Cooling & AC Supply"),
    ("Heater Core",             "ELC-010", "Electrical",     3800,  4,  "Cooling & AC Supply"),
    ("Distributor Assembly",    "ELC-011", "Electrical",     3200,  5,  "Wiring Harness Supply"),
    ("Voltage Regulator",       "ELC-012", "Electrical",     1200,  8,  "Wiring Harness Supply"),
    ("Wiring Harness Kit",      "ELC-013", "Electrical",     2800,  5,  "Wiring Harness Supply"),
    ("Relay Switch Set",        "ELC-014", "Electrical",      600, 15,  "Wiring Harness Supply"),
    ("Fuse Box Assembly",       "ELC-015", "Electrical",     1600,  6,  "Wiring Harness Supply"),

    # ── Suspension (10) ──
    ("Shock Absorber Set",      "SUS-001", "Suspension",     4500,  6,  "Suspension Kingdom"),
    ("Coil Spring Set",         "SUS-002", "Suspension",     3800,  5,  "Suspension Kingdom"),
    ("Ball Joint",              "SUS-003", "Suspension",     1200, 10,  "Suspension Kingdom"),
    ("Control Arm Bushing",     "SUS-004", "Suspension",      900, 12,  "Suspension Kingdom"),
    ("Stabilizer Link",         "SUS-005", "Suspension",      650, 15,  "Suspension Kingdom"),
    ("Tie Rod End",             "SUS-006", "Suspension",     1100, 10,  "Chassis Parts Co."),
    ("Control Arm Assembly",    "SUS-007", "Suspension",     3500,  5,  "Chassis Parts Co."),
    ("Sway Bar Bushing",        "SUS-008", "Suspension",      400, 20,  "Chassis Parts Co."),
    ("Strut Mount",             "SUS-009", "Suspension",     1500,  8,  "Chassis Parts Co."),
    ("Leaf Spring Bushing",     "SUS-010", "Suspension",      700, 12,  "Suspension Kingdom"),

    # ── Body Parts (12) ──
    ("Hood",                    "BOD-001", "Body Parts",     8500,  3,  "Body Parts Hub"),
    ("Front Bumper",            "BOD-002", "Body Parts",     6500,  4,  "Body Parts Hub"),
    ("Rear Bumper",             "BOD-003", "Body Parts",     5800,  4,  "Body Parts Hub"),
    ("Side Mirror (Left)",      "BOD-004", "Body Parts",     2500,  6,  "Body Parts Hub"),
    ("Side Mirror (Right)",     "BOD-005", "Body Parts",     2500,  6,  "Body Parts Hub"),
    ("Door Handle Set",         "BOD-006", "Body Parts",     1200, 10,  "Body Parts Hub"),
    ("Headlight Assembly",      "BOD-007", "Body Parts",     3500,  5,  "Body Parts Hub"),
    ("Tail Light Assembly",     "BOD-008", "Body Parts",     2800,  5,  "Body Parts Hub"),
    ("Fender (Left)",           "BOD-009", "Body Parts",     3200,  4,  "Fender & Panel Shop"),
    ("Fender (Right)",          "BOD-010", "Body Parts",     3200,  4,  "Fender & Panel Shop"),
    ("Grille Assembly",         "BOD-011", "Body Parts",     2200,  5,  "Fender & Panel Shop"),
    ("Radiator Support",        "BOD-012", "Body Parts",     2800,  4,  "Fender & Panel Shop"),

    # ── Engine Parts (23) ──
    ("Engine Piston Set",       "ENG-001", "Engine Parts",   4500,  4,  "Piston & Rings Co."),
    ("Piston Ring Set",         "ENG-002", "Engine Parts",   2800,  5,  "Piston & Rings Co."),
    ("Connecting Rod",          "ENG-003", "Engine Parts",   3200,  4,  "Piston & Rings Co."),
    ("Crankshaft Main Bearing", "ENG-004", "Engine Parts",   2500,  6,  "Toyota Parts Depot"),
    ("Timing Belt Kit",         "ENG-005", "Engine Parts",   3800,  5,  "Toyota Parts Depot"),
    ("Water Pump",              "ENG-006", "Engine Parts",   2200,  6,  "Toyota Parts Depot"),
    ("Oil Pump Assembly",       "ENG-007", "Engine Parts",   2800,  4,  "Toyota Parts Depot"),
    ("Fuel Injector Set",       "ENG-008", "Engine Parts",   6500,  3,  "Mitsubishi Auto Supply"),
    ("Turbocharger Assembly",   "ENG-009", "Engine Parts",  15000,  2,  "Mitsubishi Auto Supply"),
    ("Valve Cover Gasket",      "ENG-010", "Engine Parts",    450, 15,  "Mitsubishi Auto Supply"),
    ("Diesel Injector Pump",    "ENG-011", "Engine Parts",  12000,  2,  "Diesel Parts Specialist"),
    ("Glow Plug Set",           "ENG-012", "Engine Parts",   1600,  8,  "Diesel Parts Specialist"),
    ("Fuel Filter (Diesel)",    "ENG-013", "Engine Parts",    600, 12,  "Diesel Parts Specialist"),
    ("Turbo Hose Kit",          "ENG-014", "Engine Parts",   3500,  4,  "Diesel Parts Specialist"),
    ("Camshaft Assembly",       "ENG-015", "Engine Parts",   8500,  3,  "Camshaft Trading"),
    ("Valve Set",               "ENG-016", "Engine Parts",   3200,  5,  "Camshaft Trading"),
    ("Timing Chain Kit",        "ENG-017", "Engine Parts",   4200,  4,  "Camshaft Trading"),
    ("Flywheel",                "ENG-018", "Engine Parts",   5500,  3,  "Transmission Parts Co."),
    ("Clutch Kit",              "ENG-019", "Engine Parts",   6800,  4,  "Transmission Parts Co."),
    ("Clutch Release Bearing",  "ENG-020", "Engine Parts",   1800,  6,  "Transmission Parts Co."),
    ("Transmission Mount",      "ENG-021", "Engine Parts",   1200,  8,  "Transmission Parts Co."),
    ("EGR Valve",               "ENG-022", "Engine Parts",   4500,  4,  "Toyota Parts Depot"),
    ("Throttle Body",           "ENG-023", "Engine Parts",   5800,  3,  "Mitsubishi Auto Supply"),

    # ── Others (20) ──
    ("Drive Belt Set",          "OTR-001", "Others",         1500,  8,  "Universal Auto Parts"),
    ("Hose Clamp Assortment",   "OTR-002", "Others",          350, 20,  "Universal Auto Parts"),
    ("Wheel Nut Set",           "OTR-003", "Others",          600, 15,  "Universal Auto Parts"),
    ("Fuel Hose 1m",            "OTR-004", "Others",          450, 15,  "Universal Auto Parts"),
    ("Battery Terminal Set",    "OTR-005", "Others",          250, 20,  "Universal Auto Parts"),
    ("Fuse Assortment Kit",     "OTR-006", "Others",          300, 25,  "Universal Auto Parts"),
    ("Wiper Blade Set",         "OTR-007", "Others",          550, 20,  "Universal Auto Parts"),
    ("Interior LED Bulb Kit",   "OTR-008", "Others",          400, 20,  "Universal Auto Parts"),
    ("M6 Bolt Pack 50pcs",      "OTR-009", "Others",          200, 30,  "Fasteners & Hardware"),
    ("M8 Bolt Pack 50pcs",      "OTR-010", "Others",          250, 30,  "Fasteners & Hardware"),
    ("Washer Assortment",       "OTR-011", "Others",          180, 40,  "Fasteners & Hardware"),
    ("Cotter Pin Set",          "OTR-012", "Others",          120, 40,  "Fasteners & Hardware"),
    ("Ratchet Tie-Down Set",    "OTR-013", "Others",          800, 15,  "General Auto Supply"),
    ("Tire Inflator",           "OTR-014", "Others",         1200, 10,  "General Auto Supply"),
    ("Jump Start Cable",        "OTR-015", "Others",          700, 15,  "General Auto Supply"),
    ("Tool Box Set",            "OTR-016", "Others",         2500,  8,  "General Auto Supply"),
    ("Jack Stand Pair",         "OTR-017", "Others",         1800, 10,  "Universal Auto Parts"),
    ("LED Work Light",          "OTR-018", "Others",          650, 20,  "General Auto Supply"),
    ("Duct Tape Heavy Duty",    "OTR-019", "Others",          150, 30,  "Fasteners & Hardware"),
    ("Zip Tie Assortment",      "OTR-020", "Others",          120, 40,  "Fasteners & Hardware"),
]

random.seed(42)

print("Inserting 100 products...")
for i, p in enumerate(products, start=1):
    name, sku, cat, price, threshold, supplier_name = p
    qty = random.randint(3, 100)
    # Whole number price only: vary by +/-10% but keep integer
    current_price = int(price * random.uniform(0.9, 1.15))
    if current_price < 1:
        current_price = 1
    barcode = f"{random.randint(10000000, 99999999)}"

    cur.execute("SELECT id FROM suppliers WHERE name = %s", (supplier_name,))
    row = cur.fetchone()
    if not row:
        print(f"  WARNING: Supplier '{supplier_name}' not found for product '{name}'")
        continue
    sid = row[0]

    cur.execute("""
        INSERT INTO inventory (item_name, barcode, sku, category, supplier_id, quantity, threshold, price, inactive)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, barcode, sku, cat, sid, qty, threshold, current_price, 0))

conn.commit()
cur.close()
conn.close()
print(" Done! 20 suppliers and 100 products seeded.")
