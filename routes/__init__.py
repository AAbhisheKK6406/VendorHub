from flask import Blueprint

def register_blueprints(app):
    """
    Central router hub responsible for importing and mounting individual 
    feature blueprints onto the core Flask application instance.
    """
    from routes.auth_routes import auth_bp
    from routes.inventory_routes import inventory_bp
    from routes.customer_routes import customer_bp
    from routes.billing_routes import billing_bp
    from routes.report_routes import report_bp
    from routes.dashboard_routes import dashboard_bp  # 1. Localized import for dashboard

    # Registering modules with clean URL prefix boundaries
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(report_bp, url_prefix='/reports')
    
    # 2. Register the dashboard blueprint with its clean boundary
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')