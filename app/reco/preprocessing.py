"""
Preprocessing and feature engineering for the content-based recommender.

Responsibilities:
- Parse JSON genre_text into genre names
- Build a global genre vocabulary
- Encode genres into multi-hot vectors
- Normalize popularity
- Compute recency scores using exponential decay
- Export clean, model-ready CSV datasets (with overview + source_db)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from math import exp
from typing import Dict, List, Sequence, Optional, Tuple

import numpy as np
import pandas as pd

from .data_loader import MovieRecord


# =========================================================
# -------------------- GENRE PARSING ----------------------
# =========================================================


def normalize_genre_name(name: str) -> str:
    """
    Convert genre name to safe column format.
    Example: 'Science Fiction' -> 'science_fiction'
    """
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    return name


def parse_genres(genre_text: str) -> List[str]:
    """
    Parse genre JSON stored in DB.
    Expected format:
    [
      {"id": 16, "name": "Animation"},
      {"id": 10751, "name": "Family"}
    ]
    """
    if not genre_text:
        return []

    try:
        data = json.loads(genre_text)
        if isinstance(data, list):
            return [
                normalize_genre_name(g["name"])
                for g in data
                if isinstance(g, dict) and "name" in g
            ]
    except Exception:
        pass

    return []


def build_genre_vocab(movies: Sequence[MovieRecord]) -> Dict[str, int]:
    genre_set = set()
    for m in movies:
        genre_set.update(parse_genres(m.genre_text))
    return {g: i for i, g in enumerate(sorted(genre_set))}


def encode_genres_multi_hot(
    genres: Sequence[str],
    vocab: Dict[str, int],
) -> np.ndarray:
    vec = np.zeros(len(vocab), dtype=np.float32)
    for g in genres:
        idx = vocab.get(g)
        if idx is not None:
            vec[idx] = 1.0
    return vec


# =========================================================
# ---------------- POPULARITY NORMALIZER ------------------
# =========================================================


@dataclass
class PopularityNormalizer:
    min_val: float
    max_val: float

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.max_val <= self.min_val:
            return np.zeros_like(values, dtype=np.float32)
        return (values - self.min_val) / (self.max_val - self.min_val)

    @staticmethod
    def from_values(values: Sequence[float]) -> "PopularityNormalizer":
        arr = np.asarray(values, dtype=np.float32)
        return PopularityNormalizer(float(arr.min()), float(arr.max()))


# =========================================================
# ------------------- RECENCY SCORE -----------------------
# =========================================================


def compute_recency_score(
    release_date: Optional[date],
    reference_date: Optional[date] = None,
    half_life_days: float = 180.0,
) -> float:
    if release_date is None:
        return 0.0

    if reference_date is None:
        reference_date = datetime.utcnow().date()

    days_since = max((reference_date - release_date).days, 0)
    return float(exp(-days_since / half_life_days))


# =========================================================
# ------------------ FEATURE CONTAINER --------------------
# =========================================================


@dataclass
class EngineeredFeatures:
    movie_ids: np.ndarray
    titles: List[str]
    overviews: List[str]
    source_dbs: List[str]  # ✅ NEW
    movie_genre_vectors: np.ndarray
    popularity_norm: np.ndarray
    recency_scores: np.ndarray
    genre_vocab: Dict[str, int]
    popularity_normalizer: PopularityNormalizer


# =========================================================
# ------------- BASE FEATURE MATRIX BUILDER ---------------
# =========================================================


def build_movie_feature_matrix(
    movies: Sequence[MovieRecord],
) -> EngineeredFeatures:
    if not movies:
        raise ValueError("No movies provided for preprocessing.")

    genre_vocab = build_genre_vocab(movies)
    pop_norm = PopularityNormalizer.from_values([m.popularity_raw for m in movies])

    movie_ids: List[int] = []
    titles: List[str] = []
    overviews: List[str] = []
    source_dbs: List[str] = []
    genre_vecs: List[np.ndarray] = []
    pop_vals: List[float] = []
    recency_vals: List[float] = []

    for m in movies:
        movie_ids.append(m.id)
        titles.append(m.title)
        overviews.append(m.overview or "")
        source_dbs.append(m.source_db or "unknown")  # ✅ SAFE

        genre_vecs.append(
            encode_genres_multi_hot(
                parse_genres(m.genre_text),
                genre_vocab,
            )
        )

        pop_vals.append(m.popularity_raw)
        recency_vals.append(compute_recency_score(m.release_date))

    return EngineeredFeatures(
        movie_ids=np.asarray(movie_ids, dtype=np.int64),
        titles=titles,
        overviews=overviews,
        source_dbs=source_dbs,
        movie_genre_vectors=np.vstack(genre_vecs).astype(np.float32),
        popularity_norm=pop_norm.transform(
            np.asarray(pop_vals, dtype=np.float32)
        ).reshape(-1, 1),
        recency_scores=np.asarray(recency_vals, dtype=np.float32).reshape(-1, 1),
        genre_vocab=genre_vocab,
        popularity_normalizer=pop_norm,
    )


# =========================================================
# --------------------- CSV EXPORT ------------------------
# =========================================================


def build_genre_column_names(genre_vocab: Dict[str, int]) -> List[str]:
    cols = [None] * len(genre_vocab)
    for genre, idx in genre_vocab.items():
        cols[idx] = f"genre_{genre}"
    return cols


def export_movie_dataset_csv(
    engineered: EngineeredFeatures,
    output_path: str,
) -> None:
    genre_cols = build_genre_column_names(engineered.genre_vocab)

    df = pd.DataFrame(
        engineered.movie_genre_vectors,
        columns=genre_cols,
    )

    df.insert(0, "movie_id", engineered.movie_ids)
    df.insert(1, "title", engineered.titles)
    df.insert(2, "overview", engineered.overviews)
    df.insert(3, "source_db", engineered.source_dbs)  # ✅ NEW

    df["popularity_norm"] = engineered.popularity_norm.flatten()
    df["recency_score"] = engineered.recency_scores.flatten()

    df[genre_cols] = df[genre_cols].astype("int8")

    df.to_csv(output_path, index=False)

    print("✅ Movie dataset CSV exported successfully")
    print("📁 Path:", output_path)
    print("📊 Shape:", df.shape)


# =========================================================
# ------------------ USER FEATURE LOGIC -------------------
# =========================================================


def compute_genre_match_score(
    movie_genres: Sequence[str],
    user_genres: Sequence[str],
) -> float:
    user_set = {g for g in user_genres if g}
    if not user_set:
        return 0.0

    movie_set = {g for g in movie_genres if g}
    return len(user_set & movie_set) / float(len(user_set))


def build_full_feature_matrix_for_user(
    engineered: EngineeredFeatures,
    movies: Sequence[MovieRecord],
    user_genres: Sequence[str],
) -> Tuple[np.ndarray, np.ndarray]:

    # Map engineered movie ids to their row index
    id_to_eng_idx = {int(mid): i for i, mid in enumerate(engineered.movie_ids)}

    # Only process movies that exist in the trained engineered index
    known_movies = [m for m in movies if int(m.id) in id_to_eng_idx]

    if not known_movies:
        empty = np.empty((0, len(engineered.genre_vocab) * 2 + 3), dtype=np.float32)
        return empty, np.empty((0, 1), dtype=np.float32)

    indices = np.asarray(
        [id_to_eng_idx[int(m.id)] for m in known_movies], dtype=np.int64
    )

    # Slice engineered arrays to match subset
    genre_vecs = engineered.movie_genre_vectors[indices]  # (N, G)
    pop_norm = engineered.popularity_norm[indices]  # (N, 1)
    recency = engineered.recency_scores[indices]  # (N, 1)

    N = len(known_movies)

    user_vec = encode_genres_multi_hot(
        [normalize_genre_name(g) for g in user_genres],
        engineered.genre_vocab,
    )
    user_vec = np.tile(user_vec.reshape(1, -1), (N, 1))  # (N, G)

    match_scores = [
        compute_genre_match_score(
            parse_genres(m.genre_text),
            [normalize_genre_name(g) for g in user_genres],
        )
        for m in known_movies
    ]
    match_arr = np.asarray(match_scores, dtype=np.float32).reshape(-1, 1)  # (N, 1)

    X = np.concatenate(
        [genre_vecs, pop_norm, recency, user_vec, match_arr],
        axis=1,
    )

    return X, match_arr
