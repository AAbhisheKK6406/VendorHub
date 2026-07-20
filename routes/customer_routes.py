from flask import Blueprint, jsonify

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/test', methods=['GET'])
def test_customer():
    """Simple architectural health check endpoint for Customer routing."""
    return jsonify({
        "status": "online",
        "module": "Customer Blueprint Router"
    }), 200