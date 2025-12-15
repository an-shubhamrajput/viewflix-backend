from flask import Blueprint, session, render_template, request, jsonify
import json
from sqlalchemy import or_
from app.db_helper import get_model_query, models_to_dict_list, get_database_name_for_genre, model_to_dict
from sqlalchemy import or_, func
import re
from sqlalchemy.dialects.postgresql import JSONB
from app.models import PopularMovies, RecentAddedMovies, TopRatedMovies, ClassicMovies, UpcommingMovies
from app.models import MovieDetails

movie_bp = Blueprint('movie', __name__)

# =========================================================
# Helper: Ensure minimum movie count
# =========================================================
def ensure_minimum_movies(movies, genre_id, minimum=10):
    """
    Ensures at least `minimum` movies by filling missing slots from PopularMovies.
    """
    if len(movies) >= minimum:
        return movies

    missing_count = minimum - len(movies)

    fallback_query = get_model_query(PopularMovies, genre_id)
    existing_ids = [m.id for m in movies]

    fallback = (
        fallback_query
        .filter(PopularMovies.id.notin_(existing_ids))
        .limit(missing_count)
        .all()
    )

    return movies + fallback

# =========================================================
# Get Upcoming Movies
# =========================================================
@movie_bp.route('/', methods=['GET'])
def movieInfo():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    try:
        query = get_model_query(UpcommingMovies, genre_id)
        movies = query.limit(60).all()

        # Ensure at least 10 movies
        movies = ensure_minimum_movies(movies, genre_id)
        movies_list = models_to_dict_list(movies)

        session['username'] = 'shubham rajput'
        session['11'] = 123
        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# =========================================================
# Get Top Rated Movies (recent-movies)
# =========================================================
@movie_bp.route('/recent-movies', methods=['GET'])
def top_movies():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    try:
        query = get_model_query(TopRatedMovies, genre_id)
        movies = query.limit(25).all()

        movies = ensure_minimum_movies(movies, genre_id)

        movies_list = models_to_dict_list(movies)
        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# =========================================================
# Get Popular Movies
# =========================================================
@movie_bp.route('/popular', methods=['GET'])
def popular_movies():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    try:
        query = get_model_query(PopularMovies, genre_id)
        movies = query.limit(20).all()

        movies = ensure_minimum_movies(movies, genre_id)

        movies_list = models_to_dict_list(movies)
        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# =========================================================
# Get Recent Movies
# =========================================================
@movie_bp.route('/recent', methods=['GET'])
def recent_movies():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    try:
        query = get_model_query(RecentAddedMovies, genre_id)
        movies = query.limit(20).all()

        movies = ensure_minimum_movies(movies, genre_id)

        movies_list = models_to_dict_list(movies)
        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# =========================================================
# Movie Details
# =========================================================
@movie_bp.route('/details', methods=['GET'])
def movie_details():
    genre_id = request.args.get("genre_id")
    movie_id = request.args.get("movie_id")

    if not genre_id:
        return jsonify({"error": "genre_id is required"}), 400
    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    try:
        query = get_model_query(MovieDetails, genre_id)
        movie = query.filter(MovieDetails.id == movie_id).first()

        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        movie_dict = model_to_dict(movie)
        return jsonify({"movie": movie_dict})

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

# =========================================================
# Classical Movies
# =========================================================
@movie_bp.route('/classical', methods=['GET'])
def classical_movies():
    genre_id = request.args.get('genre_id')
    if not genre_id:
        return jsonify({"error": "genre_id query param is required"}), 400

    try:
        query = get_model_query(ClassicMovies, genre_id)
        movies = query.limit(20).all()

        movies = ensure_minimum_movies(movies, genre_id)

        movies_list = models_to_dict_list(movies)
        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# =========================================================
# More Like This
# =========================================================
@movie_bp.route('/more-like-this', methods=['GET'])
def more_like_this():
    movie_id = request.args.get("movie_id")
    genre_id = request.args.get("genre_id")

    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    try:
        query = get_model_query(MovieDetails, genre_id)
        movie = query.filter(MovieDetails.id == movie_id).first()

        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        # Extract genres from JSON or CSV string
        if hasattr(movie, "genres") and movie.genres:
            genres_list = json.loads(movie.genres)
            genre_ids = [g['id'] for g in genres_list if 'id' in g]

        elif hasattr(movie, "genre_ids") and movie.genre_ids:
            genre_ids = [int(g.strip()) for g in movie.genre_ids.split(",")]

        else:
            genre_ids = [18, 53]  # fallback

        if not genre_ids:
            genre_ids = [18, 53]

        base_title = re.sub(r'\s*\d+$', '', movie.title).strip()

        query_popular = get_model_query(PopularMovies, genre_id)

        genre_conditions = []
        for gid in genre_ids:
            genre_conditions.append(PopularMovies.genre_ids.like(f'{gid},%'))
            genre_conditions.append(PopularMovies.genre_ids.like(f'%,{gid},%'))
            genre_conditions.append(PopularMovies.genre_ids.like(f'%,{gid}'))
            genre_conditions.append(PopularMovies.genre_ids == str(gid))

        title_condition = PopularMovies.title.like(f'{base_title}%')

        related_movies_query = query_popular.filter(
            or_(
                or_(*genre_conditions),
                title_condition
            )
        ).order_by(PopularMovies.popularity.desc())

        related_movies = related_movies_query.all()

        seen_ids = set()
        filtered_movies = []

        # Title matches first (limit 2)
        title_matches = [m for m in related_movies if m.title.startswith(base_title)]
        for m in title_matches[:2]:
            if m.id not in seen_ids:
                filtered_movies.append(m)
                seen_ids.add(m.id)

        # Then genre matches
        for m in related_movies:
            if m.id not in seen_ids and len(filtered_movies) < 10:
                filtered_movies.append(m)
                seen_ids.add(m.id)

        movies_dict = [model_to_dict(m) for m in filtered_movies]
        return jsonify({"movies": movies_dict})

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
