import mysql.connector
con = mysql.connector.connect(host='localhost', user='root', password='00000000', database='renzrap_db')
cur = con.cursor(dictionary=True)
cur.execute("""
    SELECT i.id, i.item_name, i.quantity, i.threshold, COALESCE(s.name, '') AS supplier_name
    FROM inventory i
    LEFT JOIN suppliers s ON s.id = i.supplier_id
    WHERE i.inactive = 0
      AND (i.quantity <= 0 OR (i.threshold IS NOT NULL AND i.quantity <= i.threshold))
    ORDER BY i.quantity ASC, i.item_name ASC
""")
rows = cur.fetchall()
print(f'Count: {len(rows)}')
for r in rows:
    print(r)
cur.close()
con.close()
