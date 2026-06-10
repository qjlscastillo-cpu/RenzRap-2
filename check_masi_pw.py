"""Check masi's password."""
import hashlib
import mysql.connector
from config import DB_CONFIG

con = mysql.connector.connect(**DB_CONFIG)
cur = con.cursor(dictionary=True)
cur.execute("SELECT username, password FROM users WHERE username='masi'")
r = cur.fetchone()
print(f"Stored hash: {r['password']}")
print(f"Expected hash (00000000): {hashlib.sha256('00000000'.encode()).hexdigest()}")
print(f"Expected hash (newpass):  {hashlib.sha256('newpass'.encode()).hexdigest()}")
match_orig = r['password'] == hashlib.sha256('00000000'.encode()).hexdigest()
match_new = r['password'] == hashlib.sha256('newpass'.encode()).hexdigest()
print(f"Matches 00000000: {match_orig}")
print(f"Matches newpass:  {match_new}")
cur.close()
con.close()
