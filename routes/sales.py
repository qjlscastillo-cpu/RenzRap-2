from flask import Blueprint, render_template, session, redirect

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/sales")
def sales():
    if not session.get("logged_in"):
        return redirect("/")
    return render_template("sales.html")