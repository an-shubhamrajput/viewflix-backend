"""
Multi-database training script for the global content-based recommender.

Usage (from project root):

    # Base MySQL connection params
    export DB_HOST=127.0.0.1
    export DB_USER=...
    export DB_PASSWORD=...
    export DB_PORT=3306

    # Optional: explicit list of movie databases to include
    # (comma-separated). If not set, falls back to app.genre_config.DB_BY_GENRE.
    export RECO_MOVIE_DATABASES="tamil_movies,telugu_movies,kanada_movies,..."

    python train.py

This will:
- Connect to ALL configured movie databases.
- Load movie rows from a common table (by default `free_movies`) in each DB.
- Engineer features (genres, popularity, recency).
- Train a Linear Regression model on the unified dataset.
- Print MSE and R².
- Persist the trained model (and feature metadata) using joblib.
"""
from __future__ import annotations

from pathlib import Path

from app.reco.db_connections import get_reco_database_names
from app.reco.multi_db_loader import load_movies_multi_db
from app.reco.model import train_recommender, DEFAULT_MODEL_PATH
from app.reco.preprocessing import build_movie_feature_matrix
from app.reco.export_utils import export_preprocessed_movies_csv


# Where CSV should be saved
CSV_OUTPUT_PATH = Path("artifacts/movies_preprocessed.csv")


def main() -> None:
    db_names = get_reco_database_names()
    print(f"Training on databases: {', '.join(db_names)}")

    print("Loading movies from all databases...")
    movies = load_movies_multi_db(db_names)
    print(f"Loaded {len(movies)} movies across {len(db_names)} databases.")

    if len(movies) < 50:
        raise RuntimeError("Not enough movies to train model")

    # -----------------------------
    # FEATURE ENGINEERING
    # -----------------------------
    print("Building movie feature matrix...")
    engineered = build_movie_feature_matrix(movies)

    # -----------------------------
    # EXPORT CSV (AUTOMATIC)
    # -----------------------------
    export_preprocessed_movies_csv(
        movies=movies,
        engineered=engineered,
        output_path=CSV_OUTPUT_PATH,
    )

    # -----------------------------
    # TRAIN MODEL
    # -----------------------------
    default_user_genres = ["Action", "Drama", "Thriller", "Comedy"]

    print("Training global recommender model...")
    recommender, metrics = train_recommender(
        movies=movies,
        default_user_genres=default_user_genres,
    )

    print(f"MSE={metrics['mse']:.6f}, R²={metrics['r2']:.6f}")

    print(f"Saving model to {DEFAULT_MODEL_PATH}")
    recommender.save(DEFAULT_MODEL_PATH)
    print("Training complete.")


if __name__ == "__main__":
    main()
