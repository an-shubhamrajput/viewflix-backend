from flask import Blueprint, request, jsonify
import json
import random
from app.db_helper import get_model_query_by_db_name, models_to_dict_list, model_to_dict
from app.models import PopularMovies, RecentAddedMovies, TopRatedMovies, ClassicMovies, UpcommingMovies, MovieDetails
from app.language_config import DB_BY_LANGUAGE

movie_language_bp = Blueprint('movie_language', __name__)

# =========================================================
# Helper: Fetch movies from multiple language DBs
# =========================================================
def fetch_movies_by_languages(languages, model_class, limit=10):
    """
    Fetch movies from multiple databases corresponding to the provided languages.

    Args:
        languages (list or str): List of language names or JSON string.
        model_class: SQLAlchemy model class to query.
        limit: Max movies to fetch PER language.

    Returns:
        List of movie dictionaries with 'source_db' field injected.
    """
    if isinstance(languages, str):
        try:
            languages = json.loads(languages)
        except json.JSONDecodeError:
            return []

    if not isinstance(languages, list):
        return []

    all_movies = []

    for lang in languages:
        db_name = DB_BY_LANGUAGE.get(lang)
        if not db_name:
            continue

        try:
            query = get_model_query_by_db_name(model_class, db_name)
            movies = query.limit(limit).all()

            movies_dict_list = []
            for m in movies:
                m_dict = model_to_dict(m)
                m_dict['source_db'] = db_name  # Inject source_db
                movies_dict_list.append(m_dict)

            all_movies.extend(movies_dict_list)
        except Exception as e:
            # Log error or continue? For now, continue to next language
            print(f"[ERROR] Failed to fetch movies for language {lang} ({db_name}): {str(e)}")
            continue

    random.shuffle(all_movies)
    return all_movies


# =========================================================
# Helper: Ensure minimum movie count (adapted)
# =========================================================
def ensure_minimum_movies_distributed(movies, languages, minimum=20):
    """
    Ensures at least `minimum` movies by filling missing slots from PopularMovies
    across the provided languages.
    """
    if len(movies) >= minimum:
        return movies

    missing_count = minimum - len(movies)

    # Distribute missing count roughly equally among languages
    if not languages:
        return movies

    per_lang_limit = (missing_count // len(languages)) + 1

    fallback_movies = fetch_movies_by_languages(languages, PopularMovies, limit=per_lang_limit)

    # Filter duplicates by ID?
    # Since they are different tables/DBs, IDs might conflict or be same.
    # But usually we assume they are distinct items.
    # Simple de-duplication strategy:

    existing_ids = {m.get('id') for m in movies}

    for m in fallback_movies:
        if m.get('id') not in existing_ids:
            movies.append(m)
            existing_ids.add(m.get('id'))

        if len(movies) >= minimum:
            break

    random.shuffle(movies)
    return movies


# =========================================================
# Get Upcoming Movies
# =========================================================
@movie_language_bp.route('/', methods=['GET'])
def movieInfo_language():
    languages_param = request.args.get('languages')
    if not languages_param:
        return jsonify({"error": "languages query param is required"}), 400

    try:
        movies_list = fetch_movies_by_languages(languages_param, UpcommingMovies, limit=20)

        # Parse languages for fallback logic
        try:
            languages = json.loads(languages_param) if isinstance(languages_param, str) else languages_param
        except:
            languages = []

        movies_list = ensure_minimum_movies_distributed(movies_list, languages)

        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =========================================================
# Get Top Rated Movies (recent-movies)
# =========================================================
@movie_language_bp.route('/recent-movies', methods=['GET'])
def top_movies_language():
    languages_param = request.args.get('languages')
    if not languages_param:
        return jsonify({"error": "languages query param is required"}), 400

    try:
        movies_list = fetch_movies_by_languages(languages_param, TopRatedMovies, limit=10)

        try:
            languages = json.loads(languages_param) if isinstance(languages_param, str) else languages_param
        except:
            languages = []

        movies_list = ensure_minimum_movies_distributed(movies_list, languages)

        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =========================================================
# Get Popular Movies
# =========================================================
@movie_language_bp.route('/popular', methods=['GET'])
def popular_movies_language():
    languages_param = request.args.get('languages')
    if not languages_param:
        return jsonify({"error": "languages query param is required"}), 400

    try:
        movies_list = fetch_movies_by_languages(languages_param, PopularMovies, limit=10)

        try:
            languages = json.loads(languages_param) if isinstance(languages_param, str) else languages_param
        except:
            languages = []

        movies_list = ensure_minimum_movies_distributed(movies_list, languages)

        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =========================================================
# Get Recent Movies
# =========================================================
@movie_language_bp.route('/recent', methods=['GET'])
def recent_movies_language():
    languages_param = request.args.get('languages')
    if not languages_param:
        return jsonify({"error": "languages query param is required"}), 400

    try:
        movies_list = fetch_movies_by_languages(languages_param, RecentAddedMovies, limit=10)

        try:
            languages = json.loads(languages_param) if isinstance(languages_param, str) else languages_param
        except:
            languages = []

        movies_list = ensure_minimum_movies_distributed(movies_list, languages)

        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# =========================================================
# Classical Movies
# =========================================================
@movie_language_bp.route('/classical', methods=['GET'])
def classical_movies_language():
    languages_param = request.args.get('languages')
    if not languages_param:
        return jsonify({"error": "languages query param is required"}), 400

    try:
        movies_list = fetch_movies_by_languages(languages_param, ClassicMovies, limit=10)

        try:
            languages = json.loads(languages_param) if isinstance(languages_param, str) else languages_param
        except:
            languages = []

        movies_list = ensure_minimum_movies_distributed(movies_list, languages)

        return {"movies": movies_list}

    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
