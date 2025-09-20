from flask import Blueprint, request, jsonify, session
from models.ticket import Ticket
from functools import wraps

admin_routes = Blueprint('admin_routes', __name__)

# Simple admin credentials (change in production)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@admin_routes.route('/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return jsonify({
                'success': True,
                'message': 'Login successful'
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@admin_routes.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout endpoint"""
    session.pop('admin_logged_in', None)
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

@admin_routes.route('/tickets', methods=['GET'])
@admin_required
def get_all_tickets():
    """Get all tickets for admin dashboard"""
    try:
        tickets = Ticket.get_all()
        return jsonify({
            'success': True,
            'tickets': tickets,
            'total_count': len(tickets)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@admin_routes.route('/update_status/<int:ticket_id>', methods=['PUT'])
@admin_required
def update_ticket_status(ticket_id):
    """Update ticket status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        success = Ticket.update_status(ticket_id, new_status)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Ticket {ticket_id} status updated to {new_status}'
            }), 200
        else:
            return jsonify({'error': 'Ticket not found or invalid status'}), 404
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
