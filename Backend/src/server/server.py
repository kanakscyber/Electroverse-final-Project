from flask import Flask
from pymongo import MongoClient
import os


def create_app():
    app = Flask(__name__)

    # Config
    secret = os.environ.get('EV_SECRET_KEY', 'change_this_in_prod')
    app.config['SECRET_KEY'] = secret
    app.config['SECURE_COOKIES'] = os.environ.get('EV_SECURE_COOKIES', 'false').lower() == 'true'

    # Database
    mongo_url = os.environ.get('ev_mongo')
    db_name = os.environ.get('EV_DB_NAME', 'video_storage_db')
    if not mongo_url:
        raise RuntimeError('EV_MONGO environment variable must be set')

    client = MongoClient(mongo_url)
    db = client[db_name]
    app.config['DB'] = db

    # Helpful startup info for debugging
    try:
        total = db.videos.count_documents({})
    except Exception:
        total = 'unknown'
    print(f"Connected to MongoDB DB: {db_name} (total videos: {total})")

    # Create indexes
    try:
        db.videos.create_index('upload_date', expireAfterSeconds=604800)
        db.videos.create_index('camera_id')
        db.videos.create_index('plate_numbers')
    except Exception:
        pass
        # Register blueprints
    from src.server.users_routes import bp as users_bp
    from src.server.videos_routes import bp as videos_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(videos_bp)

    return app


if __name__ == '__main__':
    application = create_app()
    
    # Check if SSL certificates exist
    cert = os.environ.get('EV_SSL_CERT', 'localhost-cert.pem')
    key = os.environ.get('EV_SSL_KEY', 'localhost-key.pem')
    
    ssl_context = None
    if os.path.exists(cert) and os.path.exists(key):
        ssl_context = (cert, key)
        print(f"✓ Running with HTTPS on port 5000")
    else:
        print(f"✗ Running with HTTP on port 5000 (certificates not found)")
    
    application.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true',
        ssl_context=ssl_context
    )