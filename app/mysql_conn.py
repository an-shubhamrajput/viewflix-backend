from flask import current_app, g
import mysql.connector
from .genre_config import DB_BY_GENRE

def _connect(database_name: str):
    return mysql.connector.connect(
        host=current_app.config['DB_HOST'],
        user=current_app.config['DB_USER'],
        password=current_app.config['DB_PASSWORD'],
        database=database_name,
    )

def getdb():
    if not hasattr(g, '_default_db') or g._default_db is None or not g._default_db.is_connected():
        g._default_db = _connect(current_app.config['DB_DATABASE'])
    return g._default_db

def get_db_for_genre(genre_id: str):
    if not genre_id:
        raise ValueError('genre_id is required')
    database_name = DB_BY_GENRE.get(str(genre_id))
    if not database_name:
        raise ValueError(f'Unsupported genre_id: {genre_id}')
    if not hasattr(g, '_genre_dbs'):
        g._genre_dbs = {}
    conn = g._genre_dbs.get(database_name)
    if conn is None or not conn.is_connected():
        conn = _connect(database_name)
        g._genre_dbs[database_name] = conn
    return conn

def close_db(e=None):
    # close default connection
    if hasattr(g, '_default_db') and g._default_db is not None:
        try:
            if g._default_db.is_connected():
                g._default_db.close()
        finally:
            g._default_db = None
    # close any genre-scoped connections
    if hasattr(g, '_genre_dbs') and isinstance(g._genre_dbs, dict):
        for _, conn in list(g._genre_dbs.items()):
            try:
                if conn is not None and conn.is_connected():
                    conn.close()
            except Exception:
                pass
        g._genre_dbs.clear()

def init_app(app):
    app.teardown_appcontext(close_db)


