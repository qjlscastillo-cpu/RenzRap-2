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