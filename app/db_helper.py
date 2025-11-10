"""
Helper functions for database operations using SQLAlchemy models.
This module provides utilities to query models from genre-specific databases.
"""
from flask import current_app, g
from .genre_config import DB_BY_GENRE
from . import db


def get_database_name_for_genre(genre_id: str) -> str:
    """
    Get the database name for a given genre_id.

    Args:
        genre_id: The genre ID string

    Returns:
        The database name for the genre

    Raises:
        ValueError: If genre_id is not found in DB_BY_GENRE
    """
    if not genre_id:
        raise ValueError('genre_id is required')
    database_name = DB_BY_GENRE.get(str(genre_id))
    if not database_name:
        raise ValueError(f'Unsupported genre_id: {genre_id}')
    return database_name


def _get_scoped_session_for_genre(genre_id: str):
    """
    Create or retrieve a scoped SQLAlchemy session bound to the genre's engine.
    The session is stored on flask.g and removed at app context teardown.
    """
    database_name = get_database_name_for_genre(genre_id)
    if not hasattr(g, "_genre_sa_sessions"):
        g._genre_sa_sessions = {}
    session = g._genre_sa_sessions.get(database_name)
    if session is None:
        # Create a scoped session bound to the specific engine (bind)
        engine = db.get_engine(current_app, bind=database_name)
        from sqlalchemy.orm import scoped_session, sessionmaker
        session = scoped_session(sessionmaker(bind=engine))
        g._genre_sa_sessions[database_name] = session
    return session


def get_model_query(model_class, genre_id: str):
    """
    Get a query for a model using the appropriate database bind.
    This returns a query object bound to the genre's database.

    Args:
        model_class: The SQLAlchemy model class
        genre_id: The genre ID

    Returns:
        A query object bound to the genre's database
    """
    session = _get_scoped_session_for_genre(genre_id)
    return session.query(model_class)


def _close_genre_sessions(e=None):
    """Close and remove any genre-scoped SQLAlchemy sessions held on g."""
    if hasattr(g, "_genre_sa_sessions") and isinstance(g._genre_sa_sessions, dict):
        for _, session in list(g._genre_sa_sessions.items()):
            try:
                # scoped_session has remove() to dispose the current Session
                session.remove()
            except Exception:
                pass
        g._genre_sa_sessions.clear()


def init_app(app):
    """Register teardown to clean up genre-scoped SQLAlchemy sessions."""
    app.teardown_appcontext(_close_genre_sessions)


def model_to_dict(model_instance):
    """
    Convert a SQLAlchemy model instance to a dictionary.
    Excludes SQLAlchemy internal attributes.

    Args:
        model_instance: A SQLAlchemy model instance

    Returns:
        A dictionary representation of the model
    """
    if model_instance is None:
        return None

    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        result[column.name] = value
    return result


def models_to_dict_list(model_instances):
    """
    Convert a list of SQLAlchemy model instances to a list of dictionaries.

    Args:
        model_instances: A list of SQLAlchemy model instances

    Returns:
        A list of dictionaries
    """
    return [model_to_dict(instance) for instance in model_instances]


