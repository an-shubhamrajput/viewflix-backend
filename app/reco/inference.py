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
from typing import List, Sequence, Optional, Dict, Set

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
    # Filter to only movies the model knows about
    id_to_eng_idx = {
        int(mid): idx for idx, mid in enumerate(recommender.engineered.movie_ids)
    }
    known_movies = [m for m in movies if int(m.id) in id_to_eng_idx]

    if not known_movies:
        return []

    preds, genre_match_scores = recommender.predict_for_user(
        movies=known_movies, user_genres=user_genres
    )
    model_scores = preds.reshape(-1)

    scored: List[ScoredMovie] = []
    for i, m in enumerate(known_movies):
        idx = id_to_eng_idx[int(m.id)]
        scored.append(
            ScoredMovie(
                movie=m,
                model_score=float(model_scores[i]),
                popularity_norm=float(recommender.engineered.popularity_norm[idx, 0]),
                recency_score=float(recommender.engineered.recency_scores[idx, 0]),
                genre_match_score=float(genre_match_scores[i, 0]),
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


def _exclude_seen(
    scored: Sequence[ScoredMovie],
    seen_ids: Set[int],
) -> List[ScoredMovie]:
    """
    Filter out movies whose IDs are already in seen_ids.
    """
    return [s for s in scored if s.movie.id not in seen_ids]


# ============================================================================
# HOMEPAGE SECTION 1: RECOMMENDED FOR YOU
# ============================================================================


def recommended_for_you(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 25,
    seen_ids: Optional[Set[int]] = None,
) -> List[MovieRecord]:
    """
    Section 1: "Recommended for You"

    Algorithm:
    - Filter movies by genre overlap with user genres
    - Exclude already-used movie IDs (cross-section deduplication)
    - Rank using genre_match_score as primary signal
    - Return top N movies
    """
    seen_ids = seen_ids or set()

    filtered = [s for s in scored_movies if _has_genre_overlap(s.movie, user_genres)]

    if not filtered:
        print("[WARN] No genre overlap found, using all movies for recommendation")
        filtered = list(scored_movies)

    filtered = _exclude_seen(filtered, seen_ids)

    ranked = sorted(
        filtered,
        key=lambda s: (
            0.6 * s.genre_match_score
            + 0.25 * s.popularity_norm
            + 0.15 * s.recency_score
        ),
        reverse=True,
    )
    return [s.movie for s in ranked[:limit]]


# ============================================================================
# HOMEPAGE SECTION 2: TRENDING IN YOUR GENRES
# ============================================================================


def trending_in_your_genres(
    scored_movies: Sequence[ScoredMovie],
    user_genres: Sequence[str],
    limit: int = 12,
    seen_ids: Optional[Set[int]] = None,
) -> List[MovieRecord]:
    """
    Section 2: "Trending in Your Genres"

    Algorithm:
    - Filter by user genres
    - Exclude already-used movie IDs (cross-section deduplication)
    - Rank by: 0.5 * genre_match + 0.4 * popularity + 0.1 * recency
    - Return top N movies
    """
    seen_ids = seen_ids or set()

    filtered = [s for s in scored_movies if _has_genre_overlap(s.movie, user_genres)]

    if not filtered:
        print("[WARN] No genre overlap found for trending, using all movies")
        filtered = list(scored_movies)

    filtered = _exclude_seen(filtered, seen_ids)

    ranked = sorted(
        filtered,
        key=lambda s: (
            0.5 * s.genre_match_score + 0.4 * s.popularity_norm + 0.1 * s.recency_score
        ),
        reverse=True,
    )
    return [s.movie for s in ranked[:limit]]


# ============================================================================
# HOMEPAGE SECTION 3: NEW RELEASES IN GENRE
# ============================================================================


def new_releases_in_genre(
    scored_movies: Sequence[ScoredMovie],
    target_genres: Sequence[str],
    days_window: int = 60,
    limit: int = 20,
    seen_ids: Optional[Set[int]] = None,
) -> List[MovieRecord]:
    """
    Section 3: "New Releases in Your Genres"

    Algorithm:
    - Filter movies where genre matches ANY of the user's genres
    - Only include movies released in the last `days_window` days
    - Exclude already-used movie IDs (cross-section deduplication)
    - Rank using recency_score + genre_match_score

    Note:
    - Previously used only target_genres[0]; now uses all user genres.
    """
    seen_ids = seen_ids or set()
    targets = {g.lower().strip() for g in target_genres}
    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days_window)

    def _matches_genre(movie: MovieRecord) -> bool:
        movie_genres = {g.lower().strip() for g in parse_genres(movie.genre_text)}
        return not movie_genres.isdisjoint(targets)

    def _is_recent(movie: MovieRecord) -> bool:
        if movie.release_date is None:
            return False
        return movie.release_date >= cutoff

    # Primary filter: user genres + recency window
    filtered = [
        s for s in scored_movies if _matches_genre(s.movie) and _is_recent(s.movie)
    ]

    # Fallback 1: relax genre, keep recency
    if not filtered:
        print(f"[INFO] No recent movies in user genres, showing all recent movies")
        filtered = [s for s in scored_movies if _is_recent(s.movie)]

    # Fallback 2: relax recency, keep genre
    if not filtered:
        print(f"[INFO] No recent movies at all, showing all genre-matched movies")
        filtered = [s for s in scored_movies if _matches_genre(s.movie)]

    # Fallback 3: use all
    if not filtered:
        print(f"[WARN] No movies found for user genres, using top scored movies")
        filtered = list(scored_movies)

    filtered = _exclude_seen(filtered, seen_ids)

    ranked = sorted(
        filtered,
        key=lambda s: (s.recency_score + s.genre_match_score),
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

    No ML scoring — just metadata lookup.
    Order is preserved from watched_movie_ids (most recent first).
    """
    id_to_movie = {m.id: m for m in all_movies}

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
    """
    Build all homepage recommendation sections in one call.

    Movies are deduplicated across sections in priority order:
      1. recommended_for_you  (first pick)
      2. trending_in_your_genres (excludes section 1)
      3. new_releases (excludes sections 1 & 2)
      4. continue_watching (independent — uses watch history)

    Args:
        recommender: Trained recommendation model
        all_movies: Complete list of available movies
        user_genres: User's selected genre preferences
        watched_movie_ids: Optional list of recently watched movie IDs

    Returns:
        Dictionary with all homepage sections.
    """
    print(f"[INFO] Building homepage sections for user genres: {user_genres}")

    # Score all movies once
    scored = score_movies_for_user(recommender, all_movies, user_genres)

    sections = {}
    seen_ids: Set[int] = set()

    # Section 1: Recommended for You
    reco = recommended_for_you(
        scored_movies=scored,
        user_genres=user_genres,
        limit=25,
        seen_ids=seen_ids,
    )
    sections["recommended_for_you"] = reco
    seen_ids.update(m.id for m in reco)

    # Section 2: Trending in Your Genres
    trending = trending_in_your_genres(
        scored_movies=scored,
        user_genres=user_genres,
        limit=12,
        seen_ids=seen_ids,
    )
    sections["trending_in_your_genres"] = trending
    seen_ids.update(m.id for m in trending)

    # Section 3: New Releases (now uses ALL user genres, not just the first)
    new_rel = new_releases_in_genre(
        scored_movies=scored,
        target_genres=user_genres,
        days_window=60,
        limit=20,
        seen_ids=seen_ids,
    )
    sections["new_releases"] = new_rel
    seen_ids.update(m.id for m in new_rel)

    # Section 4: Continue Watching (independent of scoring)
    if watched_movie_ids:
        sections["continue_watching"] = continue_watching(
            all_movies=all_movies,
            watched_movie_ids=watched_movie_ids,
            limit=10,
        )

    print(f"[SUCCESS] Built {len(sections)} homepage sections")
    return sections
