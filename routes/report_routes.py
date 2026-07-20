from flask import Blueprint, jsonify

report_bp = Blueprint('report', __name__)

@report_bp.route('/test', methods=['GET'])
def test_report():
    """Simple architectural health check endpoint for Report routing."""
    return jsonify({
        "status": "online",
        "module": "Report Blueprint Router"
    }), 200