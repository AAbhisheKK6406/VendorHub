from flask import Blueprint, jsonify

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/test', methods=['GET'])
def test_billing():
    """Simple architectural health check endpoint for Billing routing."""
    return jsonify({
        "status": "online",
        "module": "Billing Blueprint Router"
    }), 200