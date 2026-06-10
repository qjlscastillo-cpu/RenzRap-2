"""Verify masi login and clean up leftover 'user'."""
import hashlib, mysql.connector
from config import DB_CONFIG

con = mysql.connector.connect(**DB_CONFIG)
cur = con.cursor(dictionary=True)

# Check masi
cur.execute("SELECT username, name, password FROM users WHERE username='masi'")
r = cur.fetchone()
expected_hash = hashlib.sha256('00000000'.encode()).hexdigest()
print(f"masi password matches 00000000: {r['password'] == expected_hash}")

# Remove stale 'user' Default User
cur.execute("DELETE FROM users WHERE username='user'")
print(f"Removed 'user' account: {cur.rowcount} row(s)")

con.commit()
cur.close()
con.close()
