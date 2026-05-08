from flask import Flask, render_template, request, session, redirect
import webbrowser
from threading import Timer

from db import init_db
from routes.auth import auth_bp
from routes.users import users_bp
from routes.inventory import inventory_bp
from routes.sales import sales_bp

app = Flask(__name__)
app.secret_key = "renzrap_secret_key"

# ── Register Blueprints ────────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(sales_bp)

# ── Placeholder pages ──────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("dashboard.html")

@app.route("/maintenance")
def maintenance():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("maintenance.html")

@app.route("/security")
@app.route("/about")
def aboutus():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("aboutus.html")
@app.route("/faqs")
def placeholder():
    page = request.path.strip("/").capitalize()
    return f"<h2 style='font-family:sans-serif;padding:40px'>{page} page coming soon. <a href='/dashboard'>Back to Dashboard</a></h2>"

# ── DB Test ────────────────────────────────────────────────────────────────
@app.route("/db-test")
def db_test():
    try:
        from db import get_connection
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        cur.close()
        con.close()
        return f"<h2>✅ Database connected! Users in table: {count}</h2>"
    except Exception as e:
        return f"<h2>❌ Connection failed: {str(e)}</h2>"

# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("Running at http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)