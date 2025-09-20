from flask import Flask
from database import init_db
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes

# Add CORS support
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Enable CORS for all routes
CORS(app)

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(user_routes)
app.register_blueprint(admin_routes, url_prefix='/admin')

if __name__ == '__main__':
    app.run(debug=True)