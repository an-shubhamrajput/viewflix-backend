import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import quote_plus
from flask_migrate import Migrate

from . import mysql_conn
from .genre_config import DB_BY_GENRE

# Load frontend URLs from FE_URL environment variable
frontend_urls = os.getenv("FE_URL")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
        f"mysql+pymysql://{_ENCODED_USER}:{_ENCODED_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        "pool_pre_ping": True,
    }

    @staticmethod
    def get_database_uri(database_name: str) -> str:
        return (
            f"mysql+pymysql://{Config._ENCODED_USER}:{Config._ENCODED_PASSWORD}"
            f"@{Config.DB_HOST}:{Config.DB_PORT}/{database_name}"
        )

    @staticmethod
    def get_binds() -> dict:
        binds = {None: Config.SQLALCHEMY_DATABASE_URI}
        for database_name in DB_BY_GENRE.values():
            bind_config = Config.SQLALCHEMY_ENGINE_OPTIONS.copy()
            bind_config["url"] = Config.get_database_uri(database_name)
            binds[database_name] = bind_config
        return binds


def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'  # Replace in production

    CORS(app, resources={r"/*": {"origins": frontend_urls}})

    app.config.from_object(Config)

    for key, value in os.environ.items():
        if key.isupper():
            app.config[key] = value

    app.config['SQLALCHEMY_BINDS'] = Config.get_binds()
    db.init_app(app)

    migrations_dir = os.environ.get('MIGRATIONS_DIR', 'migrations')
    Migrate(app, db, directory=migrations_dir)

    mysql_conn.init_app(app)

    return app
