from flask import Blueprint, request, jsonify
from models.ticket import Ticket

user_routes = Blueprint('user_routes', __name__)

@user_routes.route('/submit', methods=['POST'])
def submit_feedback():
    """Submit new feedback/complaint/suggestion"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'product', 'rating', 'type', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate feedback type
        valid_types = ['feedback', 'complaint', 'suggestion', 'praise', 'bug']
        if data['type'] not in valid_types:
            return jsonify({'error': 'Invalid feedback type'}), 400
        
        # Validate rating
        try:
            rating = int(data['rating'])
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Rating must be a valid number'}), 400
        
        # Create ticket
        ticket_id = Ticket.create(
            name=data['name'],
            email=data['email'],
            product=data['product'],
            rating=rating,
            ticket_type=data['type'],
            message=data['message']
        )
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'message': 'Feedback submitted successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@user_routes.route('/track/<int:ticket_id>', methods=['GET'])
def track_feedback(ticket_id):
    """Track feedback status by ticket ID"""
    try:
        ticket = Ticket.get_by_id(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Return only necessary information for user tracking
        return jsonify({
            'ticket_id': ticket['ticket_id'],
            'name': ticket['name'],
            'product': ticket['product'],
            'rating': ticket['rating'],
            'type': ticket['type'],
            'status': ticket['status'],
            'created_at': ticket['created_at'],
            'message': ticket['message']
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500