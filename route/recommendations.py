"""
Flask routes for the content-based recommender system.
"""

from flask import Blueprint, request, jsonify
from functools import lru_cache
import joblib
import os
import json
from app.reco.model import TrainedRecommender
from app.reco.inference import (
    build_homepage_sections,
    score_movies_for_user,
    recommended_for_you,
)
from app.reco.multi_db_loader import load_movies_multi_db, load_top_movies_multi_db

# ----------------------------------------------------------------------------
# Blueprint
# ----------------------------------------------------------------------------
reco_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")

MODEL_PATH = "app/reco_artifacts/content_recommender.joblib"
SIMILARITY_PATH = "app/reco_artifacts/similarity_engine.joblib"


# ----------------------------------------------------------------------------
# Cached loaders
# ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_recommender():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Run train.py first – recommender not found.")
    return TrainedRecommender.load(MODEL_PATH)


@lru_cache(maxsize=1)
def get_similarity_engine():
    if not os.path.exists(SIMILARITY_PATH):
        raise FileNotFoundError("Similarity engine missing. Train first.")
    return joblib.load(SIMILARITY_PATH)


@lru_cache(maxsize=1)
def get_all_movies():
    print("[INFO] Loading movies from all databases...")
    movies = load_movies_multi_db()
    print(f"[INFO] Loaded {len(movies)} movies")
    return movies


# ----------------------------------------------------------------------------
# HEALTH
# ----------------------------------------------------------------------------
@reco_bp.route("/health", methods=["GET"])
def health():
    recommender = get_recommender()
    movies = get_all_movies()

    return jsonify(
        {
            "status": "healthy",
            "movies": len(movies),
            "genres": sorted(recommender.engineered.genre_vocab.keys()),
        }
    )


def filter_by_language(movies, user_languages):
    """Filter movies by spoken_languages english_name. Returns all if no languages given."""
    if not user_languages:
        return movies

    langs = {l.lower().strip() for l in user_languages}

    def movie_matches(m):
        raw = getattr(m, "spoken_languages", "") or ""
        if not raw:
            return False
        try:
            entries = json.loads(raw)
            return any(
                entry.get("english_name", "").lower() in langs for entry in entries
            )
        except (json.JSONDecodeError, TypeError):
            return False

    return [m for m in movies if movie_matches(m)]


# ----------------------------------------------------------------------------
# HOMEPAGE (POST)
# ----------------------------------------------------------------------------
@reco_bp.route("/homepage", methods=["POST"])
def homepage():
    data = request.get_json(force=True)

    user_genres = data.get("user_genres")
    user_languages = data.get("user_languages", [])
    watched_ids = data.get("watched_movie_ids", [])
    limit = int(data.get("limit", 12))

    if not user_genres or not isinstance(user_genres, list):
        return jsonify({"error": "user_genres (list) is required"}), 400

    recommender = get_recommender()
    movies = get_all_movies()

    filtered_movies = filter_by_language(movies, user_languages)

    sections = build_homepage_sections(
        recommender=recommender,
        all_movies=filtered_movies,
        user_genres=user_genres,
        watched_movie_ids=watched_ids,
    )

    def serialize(m):
        return {
            "id": m.id,
            "title": m.title,
            "genres": m.genre_text,
            "overview": (m.overview or "")[:250],
            "poster_path": m.poster_path,
            "popularity": m.popularity_raw,
            "release_date": (m.release_date.isoformat() if m.release_date else None),
            "source_db": m.source_db,
        }

    return jsonify(
        {
            "user_genres": user_genres,
            "sections": {
                name: [serialize(m) for m in items[:limit]]
                for name, items in sections.items()
            },
        }
    )


# ----------------------------------------------------------------------------
# RECOMMENDED FOR YOU (POST)
# ----------------------------------------------------------------------------
@reco_bp.route("/recommended-for-you", methods=["POST"])
def recommended_for_you_api():
    data = request.get_json(force=True)

    user_genres = data.get("user_genres")
    user_languages = data.get("user_languages", [])
    limit = int(data.get("limit", 25))

    if not user_genres or not isinstance(user_genres, list):
        return jsonify({"error": "user_genres (list) is required"}), 400

    recommender = get_recommender()
    movies = get_all_movies()
    filtered_movies = filter_by_language(movies, user_languages)
    scored = score_movies_for_user(recommender, filtered_movies, user_genres)
    results = recommended_for_you(scored, user_genres, limit)

    return jsonify(
        [
            {
                "id": m.id,
                "title": m.title,
                "genres": m.genre_text,
                "overview": (m.overview or "")[:250],
                "poster_path": m.poster_path,
                "source_db": m.source_db,
            }
            for m in results
        ]
    )


# ----------------------------------------------------------------------------
# MORE LIKE THIS (GET)
# ----------------------------------------------------------------------------
@reco_bp.route("/more-like-this/<int:movie_id>", methods=["GET"])
def more_like_this(movie_id):
    limit = int(request.args.get("limit", 12))

    engine = get_similarity_engine()
    movies = engine.more_like_this(movie_id, limit=limit)

    return jsonify(
        [
            {
                "id": m.id,
                "title": m.title,
                "genres": m.genre_text,
                "overview": (m.overview or "")[:250],
                "poster_path": m.poster_path,
                "source_db": m.source_db,
            }
            for m in movies
        ]
    )


# ----------------------------------------------------------------------------
# GENRES
# ----------------------------------------------------------------------------
@reco_bp.route("/genres", methods=["GET"])
def genres():
    recommender = get_recommender()
    return jsonify(sorted(recommender.engineered.genre_vocab.keys()))


# ----------------------------------------------------------------------------
# TOP 10 MOVIES (GET)
# ----------------------------------------------------------------------------
@reco_bp.route("/top-ten", methods=["GET"])
def top_ten():
    """
    Return top 10 movies from all databases, sorted by popularity.
    """
    user_languages = [
        l.strip() for l in request.args.get("languages", "").split(",") if l.strip()
    ]
    # OPTIMIZATION: directly load top 10 from each DB to avoid loading 200k movies
    movies = load_top_movies_multi_db(limit=10)
    print("[DEBUG] MovieRecord fields:", vars(movies[0]))  # ← add this

    # Sort by popularity descending (since we might have 10 from EACH db)
    ranked = sorted(movies, key=lambda m: m.popularity_raw, reverse=True)
    filtered = filter_by_language(ranked, user_languages)
    # Take top 10
    top_movies = filtered[:10]

    return jsonify(
        [
            {
                "id": m.id,
                "title": m.title,
                "genres": m.genre_text,
                "overview": (m.overview or "")[:250],
                "poster_path": m.poster_path,
                "popularity": m.popularity_raw,
                "release_date": (
                    m.release_date.isoformat() if m.release_date else None
                ),
                "source_db": m.source_db,
            }
            for m in top_movies
        ]
    )
