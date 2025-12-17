"""
Inference and ranking utilities for the content-based recommender.

This module exposes:
- Scoring for arbitrary user genre selections
- Section-level recommendation helpers:
    * Recommended for You
    * Trending in Your Genres
    * New Releases in <Genre>
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence, Optional, Dict, Any

import numpy as np

from .data_loader import MovieRecord
from .model import TrainedRecommender
from .preprocessing import parse_genres


@dataclass
class ScoredMovie:
    """
    Container for a movie with associated scores used during ranking.
    """

    movie: MovieRecord
    model_score: float
    popularity_norm: float
    recency_score: float
    genre_match_score: float


def score_movies_for_user(
    recommender: TrainedRecommender,
    movies: Sequence[MovieRecord],
    user_genres: Sequence[str],
) -> List[ScoredMovie]:
    """
    Score all movies for a given user based on the trained model.
    """
    preds, genre_match_scores = recommender.predict_for_user(
        movies=movies, user_genres=user_genres
    )
    model_scores = preds.reshape(-1)

    # Map movie.id -> row index for quick lookup
    id_to_idx: Dict[int, int] = {
        int(mid): idx for idx, mid in enumerate(recommender.engineered.movie_ids)
    }

    scored: List[ScoredMovie] = []
    for i, m in enumerate(movies):
        idx = id_to_idx.get(int(m.id))
        if idx is None:
            # Movie not present in the engineered features
            continue
        scored.append(
            ScoredMovie(
                movie=m,
                model_score = float(model_scores[idx]),
                popularity_norm=float(recommender.engineered.popularity_norm[idx, 0]),
                recency_score=float(recommender.engineered.recency_scores[idx, 0]),
                genre_match_score=float(genre_match_scores[idx, 0]),
            )
        )
    return scored


def _has_genre_overlap(
    movie: MovieRecord,
    user_genres: Sequence[str],
) -> bool:
    movie_set = {g.lower() for g in parse_genres(movie.genre_text)}
    user_set = {g.lower() for g in user_genres}
    if not movie_set or not user_set:
        return False
    return not movie_set.isdisjoint(user_set)


def recommended_for_you(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 25,
) -> List[MovieRecord]:
    """
    Section A: "Recommended for You"

    - Filter movies by genre overlap with user genres.
    - Rank using model prediction score.
    - Return top N movies.
    """
    filtered = [
        s
        for s in scored_movies
        if _has_genre_overlap(s.movie, user_genres)
    ]

    # Fallback: if genre filtering yields nothing (e.g. only numeric genre_ids),
    # fall back to ranking all movies by model score.
    if not filtered:
        filtered = list(scored_movies)

    ranked = sorted(filtered, key=lambda s: s.model_score, reverse=True)
    return [s.movie for s in ranked[:limit]]


def trending_in_your_genres(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 12,
) -> List[MovieRecord]:
    """
    Section B: "Trending in Your Genres"

    - Filter by user genres.
    - Rank by: 0.7 * popularity_norm + 0.3 * model_score
    - Return top N movies.
    """
    filtered = [
        s
        for s in scored_movies
        if _has_genre_overlap(s.movie, user_genres)
    ]

    # Fallback: if genre filtering yields nothing, use all movies.
    if not filtered:
        filtered = list(scored_movies)

    def trending_score(s: ScoredMovie) -> float:
        return 0.7 * s.popularity_norm + 0.3 * s.model_score

    ranked = sorted(filtered, key=trending_score, reverse=True)
    return [s.movie for s in ranked[:limit]]


def new_releases_in_genre(
    scored_movies: Sequence[ScoredMovie],
    target_genre: str,
    days_window: int = 60,
    limit: int = 20,
) -> List[MovieRecord]:
    """
    Section C: "New Releases in <Genre>"

    - Filter movies where genre contains `target_genre`.
    - Only include movies released in the last `days_window` days.
    - Rank using model_score + recency_score.
    - Logic is reusable for any target genre.
    """
    target = target_genre.lower()
    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days_window)

    def _matches_genre(movie: MovieRecord) -> bool:
        return any(g.lower() == target for g in parse_genres(movie.genre_text))

    def _is_recent(movie: MovieRecord) -> bool:
        if movie.release_date is None:
            return False
        return movie.release_date >= cutoff

    # Primary filter: target genre + recency window
    filtered = [
        s
        for s in scored_movies
        if _matches_genre(s.movie) and _is_recent(s.movie)
    ]

    # Fallback 1: if nothing matches genre+recency, relax genre and use recency only.
    if not filtered:
        filtered = [s for s in scored_movies if _is_recent(s.movie)]

    # Fallback 2: if still nothing (no recent movies), use all movies.
    if not filtered:
        filtered = list(scored_movies)

    ranked = sorted(
        filtered,
        key=lambda s: (s.model_score + s.recency_score),
        reverse=True,
    )
    return [s.movie for s in ranked[:limit]]



