from __future__ import annotations
from typing import List, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_loader import MovieRecord


class MovieSimilarityEngine:
    """
    Memory-safe movie similarity engine using TF-IDF + cosine similarity.
    Similarity is computed ON DEMAND (no N×N matrix).
    """

    def __init__(self, movies: Sequence[MovieRecord]):
        self.movies = list(movies)
        self.id_to_index = {m.id: i for i, m in enumerate(self.movies)}

        # Build text corpus
        self.corpus = [
            f"{m.genre_text} {m.overview or ''}"
            for m in self.movies
        ]

        print(f"[INFO] Building TF-IDF matrix for {len(self.movies)} movies...")

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=8000,
            min_df=2,
            ngram_range=(1, 2),
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

        print("[INFO] TF-IDF matrix built successfully")
        print(f"[INFO] Vocabulary size: {len(self.vectorizer.vocabulary_)}")

    # -------------------------------------------------
    # More Like This (ON-DEMAND SIMILARITY)
    # -------------------------------------------------
    def more_like_this(
        self,
        movie_id: int,
        limit: int = 12,
        min_similarity: float = 0.1,
    ) -> List[MovieRecord]:

        idx = self.id_to_index.get(movie_id)
        if idx is None:
            return []

        # Compute similarity: (1 × N)
        scores = cosine_similarity(
            self.tfidf_matrix[idx],
            self.tfidf_matrix
        ).flatten()

        # Exclude itself
        scores[idx] = 0.0

        # Apply threshold
        valid_indices = np.where(scores >= min_similarity)[0]

        if len(valid_indices) == 0:
            return []

        # Get top-k
        top_indices = valid_indices[
            np.argsort(scores[valid_indices])[::-1][:limit]
        ]

        return [self.movies[i] for i in top_indices]

    # -------------------------------------------------
    # Batch similarity (MULTI-REFERENCE)
    # -------------------------------------------------
    def batch_more_like_this(
        self,
        movie_ids: Sequence[int],
        limit: int = 12,
    ) -> List[MovieRecord]:

        indices = [
            self.id_to_index[mid]
            for mid in movie_ids
            if mid in self.id_to_index
        ]

        if not indices:
            return []

        # Aggregate similarity using MAX similarity
        scores = cosine_similarity(
            self.tfidf_matrix[indices],
            self.tfidf_matrix
        ).max(axis=0)

        # Exclude reference movies
        scores[indices] = 0.0

        top_indices = np.argsort(scores)[::-1][:limit]

        return [self.movies[i] for i in top_indices]
