import mysql.connector
import hashlib
from datetime import datetime, timezone, timedelta
from config import DB_CONFIG

PH_TZ = timezone(timedelta(hours=8))

def ph_now():
    return datetime.now(PH_TZ)

def get_connection():
    con = mysql.connector.connect(**DB_CONFIG)
    cur = con.cursor()
    cur.execute("SET time_zone = '+08:00'")
    cur.close()
    return con

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    con = get_connection()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL DEFAULT '',
            username VARCHAR(150) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'Employee',
            inactive TINYINT(1) DEFAULT 0,
            email VARCHAR(255) DEFAULT '',
            phone VARCHAR(50) DEFAULT '',
            address TEXT,
            date_hired DATE DEFAULT NULL
        )
    """)
    for col, definition in [
        ("inactive", "TINYINT(1) DEFAULT 0"),
        ("email", "VARCHAR(255) DEFAULT ''"),
        ("phone", "VARCHAR(50) DEFAULT ''"),
        ("address", "TEXT"),
        ("date_hired", "DATE DEFAULT NULL"),
    ]:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        except Exception:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            sku VARCHAR(100) DEFAULT NULL,
            barcode VARCHAR(255) DEFAULT NULL,
            category VARCHAR(100) DEFAULT NULL,
            quantity INT DEFAULT 0,
            price DECIMAL(10, 2) DEFAULT 0.00,
            threshold INT DEFAULT 0,
            inactive TINYINT(1) DEFAULT 0,
            supplier_id INT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, definition in [
        ("sku", "VARCHAR(100) DEFAULT NULL"),
        ("barcode", "VARCHAR(255) DEFAULT NULL"),
        ("category", "VARCHAR(100) DEFAULT NULL"),
        ("threshold", "INT DEFAULT 0"),
        ("inactive", "TINYINT(1) DEFAULT 0"),
        ("supplier_id", "INT DEFAULT NULL"),
    ]:
        try:
            cur.execute(f"ALTER TABLE inventory ADD COLUMN {col} {definition}")
        except Exception:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id VARCHAR(50) PRIMARY KEY,
            items TEXT,
            subtotal DECIMAL(10, 2) DEFAULT 0.00,
            vat DECIMAL(10, 2) DEFAULT 0.00,
            total_price DECIMAL(10, 2) NOT NULL,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cur.execute("ALTER TABLE sales MODIFY COLUMN id VARCHAR(50)")
    except Exception:
        pass
    for col, definition in [
        ("items", "TEXT"),
        ("subtotal", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("vat", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("amount_received", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("change_amount", "DECIMAL(10, 2) DEFAULT 0.00"),
    ]:
        try:
            cur.execute(f"ALTER TABLE sales ADD COLUMN {col} {definition}")
        except Exception:
            pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(150) NOT NULL,
        type VARCHAR(50) NOT NULL,
        message VARCHAR(255) NOT NULL,
        link VARCHAR(255) DEFAULT NULL,
        is_read TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) DEFAULT '',
            status VARCHAR(50) DEFAULT 'Active',
            address TEXT,
            contact VARCHAR(255) DEFAULT '',
            phone VARCHAR(50) DEFAULT '',
            email VARCHAR(255) DEFAULT '',
            inactive TINYINT(1) DEFAULT 0
        )
    """)
    try:
        cur.execute("ALTER TABLE suppliers ADD COLUMN inactive TINYINT(1) DEFAULT 0 AFTER email")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE suppliers ADD COLUMN delivery_time INT DEFAULT 0 AFTER inactive")
    except Exception:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(150) NOT NULL,
            reset_code VARCHAR(6) NOT NULL,
            used TINYINT(1) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reorder_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_id INT NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            sku VARCHAR(100),
            category VARCHAR(100),
            supplier_id INT NOT NULL,
            supplier_name VARCHAR(255),
            qty_ordered INT NOT NULL DEFAULT 1,
            status ENUM('Pending','Received') DEFAULT 'Pending',
            date_requested DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_received DATETIME DEFAULT NULL
        )
    """)

    # Rename existing tables to new names (safe to run repeatedly)
    for old_name, new_name in [("backups", "maintenance")]:
        try:
            cur.execute(f"RENAME TABLE {old_name} TO {new_name}")
        except Exception:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            snapshot JSON,
            created_by VARCHAR(150),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            po_number VARCHAR(50) NOT NULL UNIQUE,
            supplier_id INT,
            supplier_name VARCHAR(255),
            status ENUM('Draft','Ordered','Received','Cancelled') DEFAULT 'Draft',
            notes TEXT,
            created_by VARCHAR(150),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            po_id INT NOT NULL,
            item_id INT,
            item_name VARCHAR(255) NOT NULL,
            sku VARCHAR(100),
            category VARCHAR(100),
            quantity INT NOT NULL DEFAULT 1,
            unit_price DECIMAL(10,2) DEFAULT 0.00,
            FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE
        )
    """)

    for old_name, new_name in [("z_readings", "reports")]:
        try:
            cur.execute(f"RENAME TABLE {old_name} TO {new_name}")
        except Exception:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            reading_number INT NOT NULL,
            total_sales DECIMAL(10, 2) DEFAULT 0.00,
            transaction_count INT DEFAULT 0,
            avg_sale DECIMAL(10, 2) DEFAULT 0.00,
            vat_total DECIMAL(10, 2) DEFAULT 0.00,
            subtotal_total DECIMAL(10, 2) DEFAULT 0.00,
            discount_total DECIMAL(10, 2) DEFAULT 0.00,
            total_items_sold INT DEFAULT 0,
            discounted_transactions INT DEFAULT 0,
            total_received DECIMAL(10, 2) DEFAULT 0.00,
            total_change DECIMAL(10, 2) DEFAULT 0.00,
            start_date DATETIME DEFAULT NULL,
            end_date DATETIME DEFAULT NULL,
            created_by VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, definition in [
        ("discount_total", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("total_items_sold", "INT DEFAULT 0"),
        ("discounted_transactions", "INT DEFAULT 0"),
        ("total_received", "DECIMAL(10, 2) DEFAULT 0.00"),
        ("total_change", "DECIMAL(10, 2) DEFAULT 0.00"),
    ]:
        try:
            cur.execute(f"ALTER TABLE reports ADD COLUMN {col} {definition}")
        except Exception:
            pass

    cur.execute("SELECT 1 FROM users WHERE username = %s", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (name, username, password, role) VALUES (%s, %s, %s, %s)",
            ("Administrator", "admin", hash_password("password123"), "Admin")
        )

    cur.execute("SELECT 1 FROM users WHERE username = %s", ("user",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (name, username, password, role) VALUES (%s, %s, %s, %s)",
            ("Default User", "user", hash_password("123"), "Employee")
        )

    con.commit()
    cur.close()
    con.close()
    print("Database initialized - all tables ready.")