"""
AI Research Assistant Agent - Main Application
Course: Agent Based Computing (SEN-330)
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from extensions import db

# Initialize extensions
from extensions import db

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = 'research-agent-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from routes.main import main_bp
    from routes.search import search_bp
    from routes.citation import citation_bp
    from routes.plagiarism import plagiarism_bp
    from routes.reference import reference_bp
    from routes.related import related_bp

    app.register_blueprint(related_bp, url_prefix='/related')
    app.register_blueprint(main_bp)
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(citation_bp, url_prefix='/citation')
    app.register_blueprint(plagiarism_bp, url_prefix='/plagiarism')
    app.register_blueprint(reference_bp, url_prefix='/reference')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=5000)