"""Test masi login end-to-end."""
from app import app

with app.test_client() as c:
    r = c.post('/login', json={'username': 'masi', 'password': '00000000'})
    print(f'Login: status={r.status_code} body={r.json}')
    # Check session directly
    with c.session_transaction() as sess:
        print(f'  session logged_in={sess.get("logged_in")} username={sess.get("username")} role={sess.get("role")}')
    # Can access profile?
    r2 = c.get('/profile')
    print(f'Profile: status={r2.status_code}')
