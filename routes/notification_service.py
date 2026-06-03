from db import get_connection

def create_notification(username, notif_type, message, link=None):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO notifications (username, type, message, link)
        VALUES (%s, %s, %s, %s)
    """, (username, notif_type, message, link))
    con.commit()
    cur.close()
    con.close()

# In notifications_service.py

def get_user_notifications(username, limit=20):
    con = get_connection()
    cur = con.cursor(dictionary=True)
    # Using CONCAT ensures Python doesn't interfere with the % symbols
    query = """
        SELECT id, type, message, link, is_read,
               DATE_FORMAT(created_at, CONCAT('%', 'b ', '%', 'd, ', '%', 'l:', '%', 'i ', '%', 'p')) AS date_label
        FROM notifications
        WHERE username = %s
        ORDER BY id DESC
        LIMIT %s
    """
    cur.execute(query, (username, limit))
    rows = cur.fetchall()
    cur.close()
    con.close()
    return rows

def get_unread_count(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE username = %s AND is_read = 0
    """, (username,))
    count = cur.fetchone()[0]
    cur.close()
    con.close()
    return count

def mark_as_read(notification_id, username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE notifications SET is_read = 1
        WHERE id = %s AND username = %s
    """, (notification_id, username))
    con.commit()
    cur.close()
    con.close()

def mark_all_read(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE notifications SET is_read = 1
        WHERE username = %s AND is_read = 0
    """, (username,))
    con.commit()
    cur.close()
    con.close()

def delete_notification(notification_id, username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        DELETE FROM notifications
        WHERE id = %s AND username = %s
    """, (notification_id, username))
    con.commit()
    cur.close()
    con.close()


def check_low_stock():
    """Check inventory for low/out-of-stock items and notify all admin users."""
    con = get_connection()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT id, item_name, quantity, threshold
        FROM inventory
        WHERE inactive = 0
    """)
    items = cur.fetchall()

    alerts = []
    for item in items:
        qty = item['quantity'] or 0
        threshold = item['threshold'] or 0
        if qty <= 0:
            alerts.append((item['id'], item['item_name'], 'Out of Stock', qty, threshold))
        elif threshold > 0 and qty <= threshold:
            alerts.append((item['id'], item['item_name'], 'Low Stock', qty, threshold))

    if not alerts:
        cur.close(); con.close()
        return

    cur.execute("SELECT username FROM users WHERE role = 'Admin'")
    admins = [r['username'] for r in cur.fetchall()]
    if not admins:
        cur.close(); con.close()
        return

    for pid, name, status, qty, threshold in alerts:
        msg = f"{status}: {name} ({qty}/{threshold})"
        link = '/inventory'

        placeholders = ', '.join(['%s'] * len(admins))
        cur.execute(f"""
            SELECT id FROM notifications
            WHERE username IN ({placeholders})
              AND type = 'inventory'
              AND message = %s
              AND is_read = 0
            LIMIT 1
        """, (*admins, msg))
        if cur.fetchone():
            continue

        for username in admins:
            cur.execute("""
                INSERT INTO notifications (username, type, message, link)
                VALUES (%s, 'inventory', %s, %s)
            """, (username, msg, link))

    con.commit()
    cur.close()
    con.close()