from flask import Blueprint, jsonify

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/test', methods=['GET'])
def test_inventory():
    """Simple architectural health check endpoint for Inventory routing."""
    return jsonify({
        "status": "online",
        "module": "Inventory Blueprint Router"
    }), 200