"""
Training script for the phase-1 content-based movie recommendation model.

Usage (from project root):

    export DB_HOST=...
    export DB_USER=...
    export DB_PASSWORD=...
    export DB_DATABASE=tamil_database   # or the appropriate DB
    python train_recommender.py

This will:
- Load movie metadata from the configured MySQL table.
- Engineer features based on genres, popularity, and recency.
- Train a Linear Regression model.
- Print basic metrics (MSE, R²).
- Persist the trained model and feature metadata to disk using joblib.
"""

from __future__ import annotations

from app.reco.data_loader import load_movies, MovieTableConfig
from app.reco.model import train_recommender, DEFAULT_MODEL_PATH


def main() -> None:
    # Map the logical "movies" schema to a real table.
    # Adjust this mapping if you want to train on a different table.
    table_cfg = MovieTableConfig(
        table_name="free_movies",
        id_column="id",
        title_column="title",
        genre_text_column="genre_text",
        popularity_column="popularity",
        release_date_column="release_date",
    )

    print("Loading movies from MySQL...")
    movies = load_movies(table_cfg)
    print(f"Loaded {len(movies)} movies.")

    if not movies:
        raise RuntimeError("No movies loaded; cannot train recommender.")

    # Default synthetic user profile for training.
    # This can be tuned based on your audience.
    default_user_genres = ["Action", "Drama", "Thriller"]

    print("Training Linear Regression recommender...")
    recommender, metrics = train_recommender(
        movies=movies, default_user_genres=default_user_genres
    )

    print(f"Training complete. MSE={metrics['mse']:.6f}, R²={metrics['r2']:.6f}")
    print(f"Saving model to: {DEFAULT_MODEL_PATH}")
    recommender.save(DEFAULT_MODEL_PATH)
    print("Model saved.")


if __name__ == "__main__":
    main()


