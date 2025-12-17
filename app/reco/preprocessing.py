"""
Preprocessing and feature engineering for the content-based recommender.

Responsibilities:
- Parse genre_text into lists of genres
- Build a global genre vocabulary
- Encode genres into multi-hot vectors
- Normalize popularity
- Compute recency scores using exponential decay:
      recency_score = exp(-days_since_release / 180)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import exp
from typing import Dict, List, Sequence, Tuple, Optional

import numpy as np

from .data_loader import MovieRecord


def parse_genres(genre_text: str) -> List[str]:
    """
    Parse a raw genre_text string into a clean list of genre names.
    Supports '|' or ',' separated formats.
    """
    if not genre_text:
        return []
    # Replace common separators with a single delimiter
    text = genre_text.replace(",", "|")
    genres = [g.strip() for g in text.split("|")]
    return [g for g in genres if g]


def build_genre_vocab(movies: Sequence[MovieRecord]) -> Dict[str, int]:
    """
    Build a stable global vocabulary mapping genre -> index.
    """
    genre_set = set()
    for m in movies:
        for g in parse_genres(m.genre_text):
            genre_set.add(g)
    sorted_genres = sorted(genre_set)
    return {genre: idx for idx, genre in enumerate(sorted_genres)}


def encode_genres_multi_hot(
    genres: Sequence[str],
    vocab: Dict[str, int],
) -> np.ndarray:
    """
    Encode a list of genres as a multi-hot numpy vector.
    """
    vec = np.zeros(len(vocab), dtype=np.float32)
    for g in genres:
        idx = vocab.get(g)
        if idx is not None:
            vec[idx] = 1.0
    return vec


@dataclass
class PopularityNormalizer:
    """
    Simple min-max normalizer for popularity.
    """

    min_val: float
    max_val: float

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.max_val <= self.min_val:
            # Degenerate case: all values are identical
            return np.zeros_like(values, dtype=np.float32)
        return (values - self.min_val) / float(self.max_val - self.min_val)

    @staticmethod
    def from_values(values: Sequence[float]) -> "PopularityNormalizer":
        arr = np.array(values, dtype=np.float32)
        return PopularityNormalizer(min_val=float(arr.min()), max_val=float(arr.max()))


def compute_recency_score(
    release_date: Optional[date],
    reference_date: Optional[date] = None,
    half_life_days: float = 180.0,
) -> float:
    """
    Compute recency score using exponential decay:
        recency_score = exp(-days_since_release / half_life_days)

    Newer movies -> score closer to 1.0, older movies -> closer to 0.0.
    """
    if release_date is None:
        return 0.0
    if reference_date is None:
        reference_date = datetime.utcnow().date()
    days_since = max((reference_date - release_date).days, 0)
    return float(exp(-days_since / half_life_days))


@dataclass
class EngineeredFeatures:
    """
    Container for engineered feature matrices and supporting metadata.
    """

    movie_ids: np.ndarray  # shape: [N]
    titles: List[str]  # length N
    movie_genre_vectors: np.ndarray  # shape: [N, G]
    popularity_norm: np.ndarray  # shape: [N, 1]
    recency_scores: np.ndarray  # shape: [N, 1]
    genre_vocab: Dict[str, int]
    popularity_normalizer: PopularityNormalizer


def build_movie_feature_matrix(
    movies: Sequence[MovieRecord],
) -> EngineeredFeatures:
    """
    Build the core movie feature matrices independent of any user.
    """
    if not movies:
        raise ValueError("No movies provided for feature engineering.")

    genre_vocab = build_genre_vocab(movies)

    popularity_values: List[float] = [m.popularity_raw for m in movies]
    pop_norm = PopularityNormalizer.from_values(popularity_values)

    movie_ids: List[int] = []
    titles: List[str] = []
    genre_vecs: List[np.ndarray] = []
    pop_norm_vals: List[float] = []
    recency_vals: List[float] = []

    for m in movies:
        genres = parse_genres(m.genre_text)
        g_vec = encode_genres_multi_hot(genres, genre_vocab)
        recency = compute_recency_score(m.release_date)

        movie_ids.append(m.id)
        titles.append(m.title)
        genre_vecs.append(g_vec)
        pop_norm_vals.append(m.popularity_raw)
        recency_vals.append(recency)

    genre_matrix = np.stack(genre_vecs, axis=0).astype(np.float32)
    pop_raw_array = np.array(pop_norm_vals, dtype=np.float32)
    pop_norm_array = pop_norm.transform(pop_raw_array).reshape(-1, 1)
    recency_array = np.array(recency_vals, dtype=np.float32).reshape(-1, 1)

    return EngineeredFeatures(
        movie_ids=np.array(movie_ids, dtype=np.int64),
        titles=titles,
        movie_genre_vectors=genre_matrix,
        popularity_norm=pop_norm_array,
        recency_scores=recency_array,
        genre_vocab=genre_vocab,
        popularity_normalizer=pop_norm,
    )


def compute_genre_match_score(
    movie_genres: Sequence[str],
    user_genres: Sequence[str],
) -> float:
    """
    genre_match_score = matched_genres / total_user_genres
    """
    user_set = {g.strip() for g in user_genres if g.strip()}
    if not user_set:
        return 0.0
    movie_set = {g.strip() for g in movie_genres if g.strip()}
    matched = user_set.intersection(movie_set)
    return float(len(matched)) / float(len(user_set))


def build_full_feature_matrix_for_user(
    engineered: EngineeredFeatures,
    movies: Sequence[MovieRecord],
    user_genres: Sequence[str],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build the full feature matrix for a specific user by combining:
        - movie_genre_vectors
        - popularity_norm
        - recency_scores
        - user_genre_vector
        - genre_match_score

    Returns:
        X: feature matrix of shape [N, G*2 + 2]
        genre_match_scores: shape [N, 1]
    """
    user_genre_vector = encode_genres_multi_hot(user_genres, engineered.genre_vocab)
    user_vec_tiled = np.tile(user_genre_vector.reshape(1, -1), (len(movies), 1))

    match_scores: List[float] = []
    for m in movies:
        movie_genres = parse_genres(m.genre_text)
        match_scores.append(compute_genre_match_score(movie_genres, user_genres))

    match_arr = np.array(match_scores, dtype=np.float32).reshape(-1, 1)

    # Concatenate: [movie_genres, popularity_norm, recency, user_genres, genre_match]
    X = np.concatenate(
        [
            engineered.movie_genre_vectors,
            engineered.popularity_norm,
            engineered.recency_scores,
            user_vec_tiled,
            match_arr,
        ],
        axis=1,
    )
    return X, match_arr



