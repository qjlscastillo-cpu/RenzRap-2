import sys, os
sys.path.append(os.path.dirname(__file__))

from flask import Flask, render_template, request, session, redirect
import webbrowser
from threading import Timer

from db import init_db
from routes.auth import auth_bp
from routes.users import users_bp
from routes.inventory import inventory_bp
from routes.reorder import reorder_bp
from routes.sales import sales_bp
from routes.security import security_bp
from routes.supplier import supplier_bp
from routes.notifications import notifications_bp
from routes.reports import reports_bp
from routes.barcodes import barcodes_bp
from routes.Maintenance import maintenance_bp
from routes.purchase_orders import purchase_bp
from routes.forgot_password import forgot_bp

app = Flask(__name__)
app.secret_key = "renzrap_secret_key"

# ── Register Blueprints ────────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(reorder_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(security_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(barcodes_bp)
app.register_blueprint(maintenance_bp)                # ← ADD THIS
app.register_blueprint(purchase_bp)
app.register_blueprint(forgot_bp)

# ── Placeholder pages ──────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("dashboard.html", active_page="dashboard", role=session.get("role"))

@app.route('/supplier')
def supplier():
    return render_template('supplier.html', active_page='supplier', role=session.get('role'))

# ── NOTE: /maintenance is now handled by maintenance_bp (removed from here) ──

@app.route("/reports")
def reports():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("reports.html", active_page="reports", role=session.get("role"))

@app.route("/history")
def history():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("history.html", active_page="history", role=session.get("role"))

@app.route("/about")
def aboutus():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("aboutus.html", active_page="about", role=session.get("role"))

@app.route("/faqs")
def faqs():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("faqs.html", active_page="faqs", role=session.get("role"))

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