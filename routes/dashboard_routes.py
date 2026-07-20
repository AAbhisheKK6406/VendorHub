# routes/dashboard_routes.py

import logging
from flask import Blueprint, render_template, session, redirect, url_for, flash

# Import existing backend service and helper functions
from services.inventory_service import get_inventory_dashboard_metrics
from services.customer_service import get_customer_dashboard_metrics
from services.billing_service import get_billing_dashboard_data
from services.reports_service import generate_low_stock_report, generate_top_selling_products

# Configure logging for tracking runtime errors
logger = logging.getLogger(__name__)

# Initialize the Flask Blueprint for the dashboard
dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
   
    
    # 1. Session Security Check
    vendor_id = session.get("vendor_id")
    vendor_name = session.get("vendor_name")
    vendor_email = session.get("vendor_email")

    if not vendor_id:
        flash("Access Denied: Please log in to access the vendor dashboard.", "danger")
        return redirect(url_for("auth.login"))

    try:
        # 2. Data Collection Layer (Calling read-only backend helper abstractions)
        inventory_res = get_inventory_dashboard_metrics(vendor_id)
        customer_res = get_customer_dashboard_metrics(vendor_id)
        billing_res = get_billing_dashboard_data(vendor_id)
        low_stock_res = generate_low_stock_report(vendor_id)
        top_products_res = generate_top_selling_products(vendor_id, limit=5)

        # 3. Formulate the Strict Structural Context Contract (dashboard_data)
        dashboard_data = {
            "vendor": {
                "id": vendor_id,
                "name": vendor_name if vendor_name else "Vendor Partner",
                "email": vendor_email if vendor_email else "N/A"
            },
            "inventory": {
                "total_products": inventory_res.get("data", {}).get("total_products", 0) if inventory_res.get("success") else 0,
                "low_stock_count": low_stock_res.get("report_data", {}).get("low_stock_items_count", 0) if low_stock_res.get("success") else 0
            },
            "customers": {
                "total_customers": customer_res.get("data", {}).get("total_customers", 0) if customer_res.get("success") else 0
            },
            "billing": {
                "total_bills": billing_res.get("data", {}).get("total_bills", 0) if billing_res.get("success") else 0,
                "today_sales": billing_res.get("data", {}).get("today_sales", 0.0) if billing_res.get("success") else 0.0,
                "monthly_revenue": billing_res.get("data", {}).get("monthly_revenue", 0.0) if billing_res.get("success") else 0.0,
                "recent_bills": billing_res.get("data", {}).get("recent_bills", []) if billing_res.get("success") else []
            },
            "reports": {
                "top_selling_products": top_products_res.get("report_data", {}).get("top_products", []) if top_products_res.get("success") else []
            }
        }

        # Check for service pipeline partial failures and notify without breaking execution
        if not (inventory_res.get("success") and customer_res.get("success") and billing_res.get("success")):
            flash("Notice: Some analytics widgets could not refresh in real time.", "warning")

        # 4. Dispatch Context to Frontend
        return render_template("dashboard.html", dashboard_data=dashboard_data)

    except Exception as unexpected_error:
        # 5. Production Exception Guard & Logging
        logger.error(f"Critical orchestrator failure on Vendor #{vendor_id} dashboard map: {str(unexpected_error)}", exc_info=True)
        flash("An unexpected error occurred while compiling your dashboard overview. Please try again later.", "danger")
        return render_template("dashboard.html", dashboard_data=None)