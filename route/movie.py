from flask import Blueprint, session, render_template, request, jsonify
import json
from sqlalchemy import or_
from app.db_helper import get_model_query, models_to_dict_list,get_database_name_for_genre, get_model_query, model_to_dict
from sqlalchemy import or_, func
import re
from sqlalchemy.dialects.postgresql import JSONB
from app.models import PopularMovies, RecentAddedMovies, TopRatedMovies, ClassicMovies
from app.db_helper import  model_to_dict
from app.models import MovieDetails

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
        movies = query.limit(25).all()

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
        movies = query.limit(20).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500



@movie_bp.route('/recent', methods=['GET'])
def recent_movies():
    """
    Get recent movies for a given genre (limited to 10).
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
        query = get_model_query(RecentAddedMovies, genre_id)
        movies = query.limit(20).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@movie_bp.route('/details', methods=['GET'])
def movie_details():
    genre_id = request.args.get("genre_id")
    movie_id = request.args.get("movie_id")
    print("genre_id:", genre_id)
    print("movie_id:", movie_id)
    if not genre_id:
        return jsonify({"error": "genre_id is required"}), 400
    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    try:
        # Assuming Movie is your SQLAlchemy model representing movies
        query = get_model_query(MovieDetails, genre_id)
        movie = query.filter(MovieDetails.id == movie_id).first()
        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        movie_dict = model_to_dict(movie)
        return jsonify({"movie": movie_dict})

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500



@movie_bp.route('/classical', methods=['GET'])
def classical_movies():
    """
    Get classical movies for a given genre (limited to 10).
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
        query = get_model_query(ClassicMovies, genre_id)
        movies = query.limit(20).all()

        # Convert SQLAlchemy models to dictionaries
        movies_list = models_to_dict_list(movies)

        return {"movies": movies_list}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500




@movie_bp.route('/more-like-this', methods=['GET'])
def more_like_this():
    movie_id = request.args.get("movie_id")
    genre_id = request.args.get("genre_id")  # For DB bind

    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    try:
        # Get movie from MovieDetails with correct bind
        query = get_model_query(MovieDetails, genre_id)
        movie = query.filter(MovieDetails.id == movie_id).first()
        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        # Extract genre IDs
        if hasattr(movie, "genres") and movie.genres:
            genres_list = json.loads(movie.genres)
            genre_ids = [g['id'] for g in genres_list if 'id' in g]
        elif hasattr(movie, "genre_ids") and movie.genre_ids:
            genre_ids = [int(g.strip()) for g in movie.genre_ids.split(",")]
        else:
            return jsonify({"error": "No genres found for the movie"}), 404

        if not genre_ids:
            return jsonify({"error": "No valid genres found"}), 404

        # Extract base title for series matching
        base_title = movie.title
        base_title = re.sub(r'\s*\d+$', '', base_title).strip()

        # Query PopularMovies with same bind
        query_popular = get_model_query(PopularMovies, genre_id)

        # Build genre matching conditions on comma-separated genre_ids string
        genre_conditions = []
        for gid in genre_ids:
            genre_conditions.append(PopularMovies.genre_ids.like(f'{gid},%'))
            genre_conditions.append(PopularMovies.genre_ids.like(f'%,{gid},%'))
            genre_conditions.append(PopularMovies.genre_ids.like(f'%,{gid}'))
            genre_conditions.append(PopularMovies.genre_ids == str(gid))

        # Build title matching condition for other parts in series
        title_condition = PopularMovies.title.like(f'{base_title}%')

        # Query movies matching genres or titles
        # Fetch all matching movies with genre or title match
        related_movies_query = query_popular.filter(
            or_(
                or_(*genre_conditions),
                title_condition
            )
        ).order_by(PopularMovies.popularity.desc())

        related_movies = related_movies_query.all()

        # Step 8: Post-processing to ensure uniqueness and include parts if multiple
        seen_ids = set()
        filtered_movies = []

        # Include movies with matching title parts first (limit 2 if multiple)
        title_part_movies = [m for m in related_movies if m.title.startswith(base_title)]
        count_title_parts = 0
        for m in title_part_movies:
            if m.id not in seen_ids:
                filtered_movies.append(m)
                seen_ids.add(m.id)
                count_title_parts += 1
                if count_title_parts >= 2:
                    break

        # Then include movies matching genres
        genre_match_movies = [m for m in related_movies if m not in filtered_movies]
        for m in genre_match_movies:
            if m.id not in seen_ids and len(filtered_movies) < 10:
                filtered_movies.append(m)
                seen_ids.add(m.id)

        # Step 9: Serialize results
        movies_dict = [model_to_dict(m) for m in filtered_movies]
        return jsonify({"movies": movies_dict})

    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

