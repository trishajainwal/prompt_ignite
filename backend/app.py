# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from database import init_db

app = Flask(__name__)
CORS(app)  # Allow frontend to call API

# Initialize database
init_db()
DB_FILE = 'feedback.db'

# Save new feedback
@app.route('/feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'email', 'type', 'rating', 'message', 'date', 'sentiment']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO feedback (name, email, product, type, rating, message, date, sentiment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['email'],
            data.get('product', ''),  # product might be optional
            data['type'],
            data['rating'],
            data['message'],
            data['date'],
            data['sentiment']
        ))
        conn.commit()
        feedback_id = c.lastrowid
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Feedback saved successfully",
            "id": feedback_id
        })
        
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

# Get all feedback
@app.route('/feedback', methods=['GET'])
def get_feedback():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT name, email, product, type, rating, message, date, sentiment FROM feedback ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        
        feedback_list = []
        for row in rows:
            feedback_list.append({
                "name": row[0],
                "email": row[1],
                "product": row[2],
                "type": row[3],
                "rating": row[4],
                "message": row[5],
                "date": row[6],
                "sentiment": row[7]
            })
        
        return jsonify(feedback_list)
        
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, host='localhost', port=5000)