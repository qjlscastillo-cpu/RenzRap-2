import mysql.connector
import hashlib
from config import DB_CONFIG

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

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
    try:
        cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT '' AFTER inactive")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(50) DEFAULT '' AFTER email")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN address TEXT AFTER phone")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN date_hired DATE DEFAULT NULL AFTER address")
    except Exception:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            barcode VARCHAR(255) DEFAULT NULL,
            quantity INT DEFAULT 0,
            price DECIMAL(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cur.execute("ALTER TABLE inventory ADD COLUMN barcode VARCHAR(255) DEFAULT NULL AFTER item_name")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE inventory ADD COLUMN inactive TINYINT(1) DEFAULT 0 AFTER threshold")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE inventory ADD COLUMN supplier_id INT DEFAULT NULL AFTER category")
    except Exception:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            quantity_sold INT NOT NULL,
            total_price DECIMAL(10, 2) NOT NULL,
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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