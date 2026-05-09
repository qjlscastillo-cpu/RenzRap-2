from db import get_connection
from flask import session

def create_logs_table():
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(150),
                role VARCHAR(50),
                action VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()
        cur.close()
        con.close()
    except Exception as e:
        print(f"Table creation error: {e}")

def log_action(action):
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO activity_logs (username, role, action) VALUES (%s, %s, %s)",
            (
                session.get("username", "Unknown"),
                session.get("role", "Unknown"),
                action
            )
        )
        con.commit()
        cur.close()
        con.close()
    except Exception as e:
        print(f"Logging error: {e}")

# Auto-create table when logger.py is imported
create_logs_table()