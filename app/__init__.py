import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # Import text function from SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import quote_plus
from . import mysql_conn
from .genre_config import DB_BY_GENRE


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Load environment variables from .env located at project root (if present)
load_dotenv(PROJECT_ROOT / '.env', override=True)


db = SQLAlchemy()

def _get_env_value(key: str) -> str:
    """Fetch a required environment variable or raise a descriptive error."""
    value = os.environ.get(key)
    if value is None or value == "":
        raise RuntimeError(f"Environment variable '{key}' is required but not set.")
    return value

class Config:
    DB_HOST = _get_env_value('DB_HOST')
    DB_USER = _get_env_value('DB_USER')
    DB_PASSWORD = _get_env_value('DB_PASSWORD')
    DB_DATABASE = _get_env_value('DB_DATABASE')
    DB_PORT = int(os.environ.get('DB_PORT', '3306'))
    SSL_CA_PATH = os.environ.get('SSL_CA_PATH')

    _ENCODED_USER = quote_plus(DB_USER)
    _ENCODED_PASSWORD = quote_plus(DB_PASSWORD)

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_ENCODED_USER}:{_ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def get_database_uri(database_name: str) -> str:
        """Generate database URI for a given database name"""
        return (
            f"mysql+pymysql://{Config._ENCODED_USER}:{Config._ENCODED_PASSWORD}@"
            f"{Config.DB_HOST}:{Config.DB_PORT}/{database_name}"
        )
    
    @staticmethod
    def get_binds() -> dict:
        """Generate SQLAlchemy binds configuration for all databases"""
        binds = {}
        # Add default database
        binds[None] = Config.SQLALCHEMY_DATABASE_URI
        # Add all genre-specific databases
        for database_name in DB_BY_GENRE.values():
            binds[database_name] = Config.get_database_uri(database_name)
        return binds

def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'  # Use a strong random secret in production

    CORS(app, resources={r"/*": {"origins": "*"}})

    app.config.from_object(Config)
    # Configure multiple database bindings
    app.config['SQLALCHEMY_BINDS'] = Config.get_binds()
    db.init_app(app)
    mysql_conn.init_app(app)
    
    # Import models to register them with SQLAlchemy
    from .models import (
        MovieRating, PopularMovies, RecentAddedMovies, TopRatedMovies,
        UpcommingMovies, MovieDetails, FreeMoviesDetails, TmdbFreeMovies, Videos
    )

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
