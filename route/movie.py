from flask import Blueprint, session, render_template, request, jsonify
from app.db_helper import get_model_query, models_to_dict_list
from app.models import PopularMovies, RecentAddedMovies, TopRatedMovies

movie_bp = Blueprint('movie', __name__)

@movie_bp.route('/', methods=['GET'])
def movieInfo():
    """
    Get popular movies for a given genre.
    Uses SQLAlchemy model instead of raw SQL.
    """
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    print("genre_id:", genre_id)
    try:
        # Use SQLAlchemy model query instead of raw SQL
        query = get_model_query(PopularMovies, genre_id)
        movies = query.limit(60).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        session['username'] = 'shubham rajput'
        session['11'] = 123
        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@movie_bp.route('/recent-movies', methods=['GET'])
def top_movies():
    """
    Get recently added movies for a given genre.
    Uses SQLAlchemy model instead of raw SQL.
    """
    print("Inside recent movies")
    print("Request args:", request.args)
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    print("genre_id:", genre_id)
    try:
        # Use SQLAlchemy model query instead of raw SQL
        query = get_model_query(TopRatedMovies, genre_id)
        movies = query.limit(10).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@movie_bp.route('/popular', methods=['GET'])
def popular_movies():
    """
    Get popular movies for a given genre (limited to 10).
    Uses SQLAlchemy model instead of raw SQL.
    """
    print("Inside popular movies")
    print("Request args:", request.args)
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    print("genre_id:", genre_id)
    try:
        # Use SQLAlchemy model query instead of raw SQL
        query = get_model_query(PopularMovies, genre_id)
        movies = query.limit(10).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500



