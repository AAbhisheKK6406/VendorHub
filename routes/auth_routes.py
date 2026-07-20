from flask import Blueprint, render_template, request, redirect, url_for, flash, session
# Reusing your pre-tested authentication service engine
from services.auth_service import login_vendor, register_vendor

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Renders the decoupled frontend vendor login interface."""
    # Redirect to dashboard if the session token is already active
    if 'vendor_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_process():
    """Handles the form submission by passing data straight to the service layer."""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    # Basic server-side guard sanity check
    if not email or not password:
        flash("Please fill in all fields.", "danger")
        return redirect(url_for('auth.login_page'))

    try:
        # FIXED: Passing parameters positionally without keyword labels (email, password)
        # to satisfy the backend function definition regardless of parameter names.
        auth_res = login_vendor(email, password)

        if auth_res.get('success'):
            # Safely pin the vendor state vectors to the client session cookie
            session.clear()
            session['vendor_id'] = auth_res.get('vendor_id', 1) # Fallback to core vendor context
            session['vendor_name'] = auth_res.get('vendor_name', 'Authorized Vendor')
            
            return redirect('/dashboard')
        else:
            # Capture the exact domain exception thrown by the engine
            error_msg = auth_res.get('message', 'Invalid email or password.')
            flash(error_msg, "danger")
            return redirect(url_for('auth.login_page'))

    except Exception as err:
        flash(f"Authentication system encounter: {str(err)}", "danger")
        return redirect(url_for('auth.login_page'))

@auth_bp.route('/logout', methods=['GET'])
def logout():
    """Clears the session tracking token and handles the exit trajectory."""
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/register', methods=['GET'])
def register_page():
    """Renders the decoupled frontend vendor onboarding registration interface."""
    if 'vendor_id' in session:
        return redirect('/dashboard')
    return render_template('register.html')

@auth_bp.route('/register', methods=['POST'])
def register_process():
    """Processes vendor onboarding inputs by passing vectors straight to the backend service."""
    username = request.form.get('username', '').strip()
    business_name = request.form.get('business_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip() or None  # Keep optional field clean
    password = request.form.get('password', '')

    # Core proxy request call execution layer targeting the backend monolith directly
    try:
        reg_res = register_vendor(
            username=username,
            email=email,
            password=password,
            business_name=business_name,
            phone=phone
        )

        if reg_res.get('success'):
            flash("Registration successful! Please login with your new credentials.", "success")
            return redirect(url_for('auth.login_page'))
        else:
            # Route processing error output mapping straight from engine response values
            error_msg = reg_res.get('message', 'Registration processing failed.')
            flash(error_msg, "danger")
            return redirect(url_for('auth.register_page'))

    except Exception as err:
        flash(f"Account registration layer error encounter: {str(err)}", "danger")
        return redirect(url_for('auth.register_page'))