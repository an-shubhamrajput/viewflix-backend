"""
Inference and ranking utilities for the content-based recommender.

This module provides all homepage recommendation sections:
1. Recommended for You
2. Trending in Your Genres
3. New Releases in Genre
4. Continue Watching (metadata only)
5. More Like This (via similarity engine)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence, Optional, Dict

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

    Args:
        recommender: Trained recommendation model
        movies: List of movies to score
        user_genres: User's selected genre preferences

    Returns:
        List of ScoredMovie objects with all computed scores
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
                model_score=float(model_scores[idx]),
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
    """
    Check if movie has any genre overlap with user's preferences.
    """
    movie_set = {g.lower().strip() for g in parse_genres(movie.genre_text)}
    user_set = {g.lower().strip() for g in user_genres}
    if not movie_set or not user_set:
        return False
    return not movie_set.isdisjoint(user_set)


# ============================================================================
# HOMEPAGE SECTION 1: RECOMMENDED FOR YOU
# ============================================================================

def recommended_for_you(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 25,
) -> List[MovieRecord]:
    """
    Section 1: "Recommended for You"

    Algorithm:
    - Filter movies by genre overlap with user genres
    - Rank using model prediction score
    - Return top N movies

    Args:
        scored_movies: Pre-scored movies
        user_genres: User's selected genre preferences
        limit: Maximum number of recommendations

    Returns:
        Top recommended movies for the user
    """
    filtered = [
        s
        for s in scored_movies
        if _has_genre_overlap(s.movie, user_genres)
    ]

    # Fallback: if genre filtering yields nothing (e.g. only numeric genre_ids),
    # fall back to ranking all movies by model score.
    if not filtered:
        print("[WARN] No genre overlap found, using all movies for recommendation")
        filtered = list(scored_movies)

    ranked = sorted(filtered, key=lambda s: s.model_score, reverse=True)
    return [s.movie for s in ranked[:limit]]


# ============================================================================
# HOMEPAGE SECTION 2: TRENDING IN YOUR GENRES
# ============================================================================

def trending_in_your_genres(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 12,
) -> List[MovieRecord]:
    """
    Section 2: "Trending in Your Genres"

    Algorithm:
    - Filter by user genres
    - Rank by: 0.7 * popularity_norm + 0.3 * model_score
    - Return top N movies

    Args:
        scored_movies: Pre-scored movies
        user_genres: User's selected genre preferences
        limit: Maximum number of trending movies

    Returns:
        Top trending movies in user's genres
    """
    filtered = [
        s
        for s in scored_movies
        if _has_genre_overlap(s.movie, user_genres)
    ]

    # Fallback: if genre filtering yields nothing, use all movies
    if not filtered:
        print("[WARN] No genre overlap found for trending, using all movies")
        filtered = list(scored_movies)

    def trending_score(s: ScoredMovie) -> float:
        return 0.7 * s.popularity_norm + 0.3 * s.model_score

    ranked = sorted(filtered, key=trending_score, reverse=True)
    return [s.movie for s in ranked[:limit]]


# ============================================================================
# HOMEPAGE SECTION 3: NEW RELEASES IN GENRE
# ============================================================================

def new_releases_in_genre(
    scored_movies: Sequence[ScoredMovie],
    target_genre: str,
    days_window: int = 60,
    limit: int = 20,
) -> List[MovieRecord]:
    """
    Section 3: "New Releases in <Genre>"

    Algorithm:
    - Filter movies where genre contains `target_genre`
    - Only include movies released in the last `days_window` days
    - Rank using model_score + recency_score

    Args:
        scored_movies: Pre-scored movies
        target_genre: Specific genre to filter by (e.g., "Action", "Romance")
        days_window: Number of days to look back for "new" releases
        limit: Maximum number of new releases

    Returns:
        Top new releases in the specified genre

    Note:
        Logic is reusable for any target genre.
    """
    target = target_genre.lower().strip()
    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days_window)

    def _matches_genre(movie: MovieRecord) -> bool:
        return any(g.lower().strip() == target for g in parse_genres(movie.genre_text))

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

    # Fallback 1: if nothing matches genre+recency, relax genre and use recency only
    if not filtered:
        print(f"[INFO] No recent movies in genre '{target_genre}', showing all recent movies")
        filtered = [s for s in scored_movies if _is_recent(s.movie)]

    # Fallback 2: if still nothing (no recent movies), use all movies matching genre
    if not filtered:
        print(f"[INFO] No recent movies at all, showing all '{target_genre}' movies")
        filtered = [s for s in scored_movies if _matches_genre(s.movie)]

    # Fallback 3: if still nothing, use top scored movies
    if not filtered:
        print(f"[WARN] No movies found for genre '{target_genre}', using top scored movies")
        filtered = list(scored_movies)

    ranked = sorted(
        filtered,
        key=lambda s: (s.model_score + s.recency_score),
        reverse=True,
    )
    return [s.movie for s in ranked[:limit]]


# ============================================================================
# HOMEPAGE SECTION 4: CONTINUE WATCHING
# ============================================================================

def continue_watching(
    all_movies: Sequence[MovieRecord],
    watched_movie_ids: Sequence[int],
    limit: int = 10,
) -> List[MovieRecord]:
    """
    Section 4: "Continue Watching"

    This section is provided by frontend (watch history).
    Backend only returns metadata for the movies.

    Args:
        all_movies: Complete list of movies
        watched_movie_ids: List of movie IDs from user's watch history
        limit: Maximum number of movies to return

    Returns:
        MovieRecord objects for recently watched movies

    Note:
        No ML scoring - just metadata lookup.
        Order is preserved from watched_movie_ids (most recent first).
    """
    # Build lookup map
    id_to_movie = {m.id: m for m in all_movies}

    # Retrieve movies in the order provided by frontend
    continue_list = []
    for movie_id in watched_movie_ids[:limit]:
        movie = id_to_movie.get(movie_id)
        if movie:
            continue_list.append(movie)

    return continue_list


# ============================================================================
# UTILITY: BUILD ALL HOMEPAGE SECTIONS
# ============================================================================

def build_homepage_sections(
    recommender: TrainedRecommender,
    all_movies: Sequence[MovieRecord],
    user_genres: Sequence[str],
    watched_movie_ids: Optional[Sequence[int]] = None,
) -> Dict[str, List[MovieRecord]]:
    print(f"[INFO] Building homepage sections for user genres: {user_genres}")
    print(f"[INFO] Building homepage sections for user watched id: {watched_movie_ids}")
    """
    Build all homepage recommendation sections in one call.

    Args:
        recommender: Trained recommendation model
        all_movies: Complete list of available movies
        user_genres: User's selected genre preferences
        watched_movie_ids: Optional list of recently watched movie IDs

    Returns:
        Dictionary with all homepage sections:
        - "recommended_for_you"
        - "trending_in_your_genres"
        - "new_releases" (uses first user genre as target)
        - "continue_watching" (if watched_movie_ids provided)
    """
    print(f"[INFO] Building homepage sections for user genres: {user_genres}")

    # Score all movies once
    scored = score_movies_for_user(recommender, all_movies, user_genres)

    sections = {}

    # Section 1: Recommended for You
    sections["recommended_for_you"] = recommended_for_you(
        scored_movies=scored,
        user_genres=user_genres,
        limit=25,
    )

    # Section 2: Trending in Your Genres
    sections["trending_in_your_genres"] = trending_in_your_genres(
        scored_movies=scored,
        user_genres=user_genres,
        limit=12,
    )

    # Section 3: New Releases (use first user genre as target)
    target_genre = user_genres[0] if user_genres else "Action"
    sections["new_releases"] = new_releases_in_genre(
        scored_movies=scored,
        target_genre=target_genre,
        days_window=60,
        limit=20,
    )

    # Section 4: Continue Watching (if watch history provided)
    if watched_movie_ids:
        sections["continue_watching"] = continue_watching(
            all_movies=all_movies,
            watched_movie_ids=watched_movie_ids,
            limit=10,
        )

    print(f"[SUCCESS] Built {len(sections)} homepage sections")
    return sections