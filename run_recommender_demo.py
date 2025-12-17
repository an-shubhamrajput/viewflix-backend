"""
Simple inference demo script for the content-based recommender.

This script:
- Loads the trained model from disk.
- Reloads the same movie metadata from MySQL.
- Scores all movies for a sample user genre profile.
- Prints the top recommendations for each homepage section:
    * Recommended for You
    * Trending in Your Genres
    * New Releases in Action
"""

from __future__ import annotations

from typing import List

from app.reco.db_connections import get_reco_database_names
from app.reco.multi_db_loader import load_movies_multi_db
from app.reco.inference import (
    score_movies_for_user,
    recommended_for_you,
    trending_in_your_genres,
    new_releases_in_genre,
)
from app.reco.model import TrainedRecommender


def _print_section(title: str, movies: List) -> None:
    print(f"\n=== {title} (top {len(movies)}) ===")
    for m in movies:
        print(f"- {m.id}: {m.title}  [{m.genre_text}]")


def main() -> None:
    db_names = get_reco_database_names()
    print(f"Loading movies from databases: {', '.join(db_names)}")
    movies = load_movies_multi_db(db_names)
    print(f"Loaded {len(movies)} movies across {len(db_names)} databases.")

    if not movies:
        raise RuntimeError("No movies available for inference.")

    print("Loading trained recommender model...")
    recommender = TrainedRecommender.load()

    # Example user genres; in production, pass in the real user's selections.
    # user_genres = ["Horror", "Drama","Action","Comedy","Romance"]
    user_genres = ["Drama"]

    print(f"Scoring movies for user genres: {user_genres}")

    scored = score_movies_for_user(recommender, movies, user_genres=user_genres)

    # Section A: Recommended for You
    rec_for_you = recommended_for_you(scored, user_genres=user_genres, limit=25)
    _print_section("Recommended for You", rec_for_you)

    # Section B: Trending in Your Genres
    trending = trending_in_your_genres(scored, user_genres=user_genres, limit=25)
    _print_section("Trending in Your Genres", trending)

    # Section C: New Releases in Action (reusable for any genre)
    new_action = new_releases_in_genre(
        scored, target_genre="Action", days_window=60, limit=25
    )
    _print_section("New Releases in Action", new_action)


if __name__ == "__main__":
    main()


