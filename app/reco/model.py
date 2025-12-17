"""
Model training, evaluation, and persistence for the content-based recommender.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple, List

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .data_loader import MovieRecord
from .preprocessing import (
    EngineeredFeatures,
    build_movie_feature_matrix,
    build_full_feature_matrix_for_user,
)


DEFAULT_MODEL_PATH = os.environ.get(
    "RECO_MODEL_PATH",
    # Store under a dedicated artifacts directory by default
    str(Path(__file__).resolve().parent.parent / "reco_artifacts" / "content_recommender.joblib"),
)


@dataclass
class TrainedRecommender:
    """
    Bundle together the trained model and all metadata needed for inference.
    """

    model: LinearRegression
    engineered: EngineeredFeatures

    def predict_for_user(
        self,
        movies: Sequence[MovieRecord],
        user_genres: Sequence[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute predicted relevance scores and genre_match_scores
        for a given user's genres.
        """
        X, genre_match_scores = build_full_feature_matrix_for_user(
            engineered=self.engineered,
            movies=movies,
            user_genres=user_genres,
        )
        preds = self.model.predict(X).reshape(-1, 1).astype(np.float32)
        return preds, genre_match_scores

    def save(self, path: str = DEFAULT_MODEL_PATH) -> None:
        """
        Persist the trained model and metadata using joblib.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, p)

    @staticmethod
    def load(path: str = DEFAULT_MODEL_PATH) -> "TrainedRecommender":
        """
        Load a saved recommender from disk.
        """
        return joblib.load(path)


def _compute_relevance_labels(
    popularity_norm: np.ndarray,
    recency_scores: np.ndarray,
    genre_match_scores: np.ndarray,
) -> np.ndarray:
    """
    Compute the target label:

        relevance =
          0.5 * genre_match_score +
          0.3 * popularity_norm +
          0.2 * recency_score
    """
    return (
        0.5 * genre_match_scores
        + 0.3 * popularity_norm
        + 0.2 * recency_scores
    ).astype(np.float32)


def train_recommender(
    movies: Sequence[MovieRecord],
    default_user_genres: Sequence[str],
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[TrainedRecommender, dict]:
    """
    Train a simple Linear Regression model on engineered features.

    The model learns to approximate the explicit relevance function using a
    default synthetic user genre profile.

    Returns:
        trained_recommender
        metrics: {"mse": ..., "r2": ...}
    """
    engineered = build_movie_feature_matrix(movies)

    # Build full feature matrix for the default synthetic user
    X, genre_match_scores = build_full_feature_matrix_for_user(
        engineered=engineered,
        movies=movies,
        user_genres=default_user_genres,
    )

    y = _compute_relevance_labels(
        popularity_norm=engineered.popularity_norm,
        recency_scores=engineered.recency_scores,
        genre_match_scores=genre_match_scores,
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mse = float(mean_squared_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    recommender = TrainedRecommender(model=model, engineered=engineered)
    metrics = {"mse": mse, "r2": r2}
    return recommender, metrics



