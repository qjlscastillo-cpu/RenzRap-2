from flask import Blueprint, render_template, session, redirect

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/inventory")
def inventory():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("inventory.html")