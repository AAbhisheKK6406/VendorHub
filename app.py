# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key_here'  # Required for Flask sessions and flashing messages

# Complete Mock Data matching all your dashboard layout requirements
DASHBOARD_DATA = {
    "vendor": {"name": "Sharma Organics"},
    
    "inventory": {
        "total_products": 1250,
        "low_stock_count": 4
    },
    
    "customers": {
        "total_customers": 342
    },
    
    "billing": {
        "total_bills": 48,
        "today_sales": 45230.50,
        "monthly_revenue": 245600.00,
        "recent_bills": [
            {"sale_id": "1001", "customer_name": "Amit Shah", "sale_date": "2026-07-19", "total_amount": 1200.50, "payment_status": "Paid"},
            {"sale_id": "1002", "customer_name": "Riya Patel", "sale_date": "2026-07-18", "total_amount": 850.00, "payment_status": "Unpaid"}
        ]
    },
    
    "reports": {
        "top_selling_products": [
            {"product_name": "Organic Tomatoes", "product_id": "P-001", "total_quantity_sold": 150},
            {"product_name": "Fresh Milk", "product_id": "P-002", "total_quantity_sold": 95}
        ]
    },
    
    # Used for Low Stock Table
    "inventory_report_items": [
        {"product_name": "Organic Tomatoes", "current_quantity": 5, "low_stock_limit": 10},
        {"product_name": "Green Chillies", "current_quantity": 2, "low_stock_limit": 5}
    ]
}

@app.route('/')
def home():
    """Renders the public landing page."""
    return render_template('home.html', title="Welcome to VendorHub")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles login page rendering and authentication form submission.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simple mock authentication check (Replace with auth_service call when backend service is linked)
        if email and password:
            session['vendor_id'] = "1"
            session['vendor_name'] = DASHBOARD_DATA["vendor"]["name"]
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            
    return render_template('login.html', title="Login - VendorHub")

@app.route('/register')
def register():
    """Renders the registration interface."""
    return render_template('register.html', title="Register - VendorHub")

@app.route('/dashboard')
def dashboard():
    """
    Protected Dashboard Route. Redirects to login if session is missing.
    """
    if 'vendor_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))
        
    return render_template(
        'dashboard.html', 
        title="Vendor Dashboard", 
        dashboard_data=DASHBOARD_DATA
    )

@app.route('/auth/logout')
def logout():
    """
    Destroys the active Flask session and redirects to Login.
    """
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/inventory')
def inventory():
    """
    Renders the dedicated Inventory Management page.
    """
    return render_template(
        'inventory.html',
        title="Inventory Management"
    )

@app.route('/customer')
def customer():
    """
    Renders the dedicated Customer Management page.
    """
    return render_template(
        'customers.html',
        title="Customer Management"
    )

@app.route('/billing')
def billing():
    """
    Renders the dedicated Billing Management page.
    """
    return render_template(
        'billing.html',
        title="Billing Management"
    )

@app.route('/reports')
def reports():
    """
    Renders the dedicated Reports & Analytics page.
    """
    return render_template(
        'reports.html',
        title="Reports & Analytics"
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)