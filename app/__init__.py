import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # Import text function from SQLAlchemy
from flask import Flask
from flask_cors import CORS
from . import mysql_conn


db = SQLAlchemy()

class Config:
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '123india')
    DB_DATABASE = os.environ.get('DB_DATABASE', 'telugu_movies')
    SSL_CA_PATH = os.environ.get('SSL_CA_PATH', '/etc/ssl/certs/ca-certificates.crt')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'  # Use a strong random secret in production

    CORS(app, resources={r"/*": {"origins": "*"}})

    app.config.from_object(Config)
    db.init_app(app)
    mysql_conn.init_app(app)

    with app.app_context():
        try:
            # Only check that Flask app spins; SQLAlchemy session isn't used elsewhere
            print("App initialized")
        except Exception as e:
            print(f"Initialization issue: {e}")

    # Register blueprints here if any
    # from app.routes.movie import movie_bp
    # app.register_blueprint(movie_bp, url_prefix='/movie')

    @app.route('/')
    def home():
        return 'Hello from Flask!'

    return app
