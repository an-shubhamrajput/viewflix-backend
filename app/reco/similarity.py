"""
Movie similarity engine for "More Like This" recommendations.

Uses TF-IDF + cosine similarity on movie genres and overview text.
Works across all databases - similar movies can come from any source_db.
"""

from __future__ import annotations

from typing import List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_loader import MovieRecord


class MovieSimilarityEngine:
    """
    Compute movie-to-movie similarity using TF-IDF on genres + overview.

    Features:
    - Handles empty overviews gracefully
    - Works across movies from different databases
    - Fast lookups via pre-computed similarity matrix
    """

    def __init__(self, movies: Sequence[MovieRecord]):
        """
        Initialize the similarity engine.

        Args:
            movies: List of all MovieRecord objects to index
        """
        self.movies = list(movies)
        self.id_to_index = {m.id: i for i, m in enumerate(self.movies)}

        # Build corpus: combine genres and overview
        # Handle empty overviews gracefully
        self.corpus = [
            f"{m.genre_text} {m.overview if m.overview else ''}"
            for m in self.movies
        ]

        print(f"[INFO] Building TF-IDF matrix for {len(self.movies)} movies...")

        # TF-IDF vectorization
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=8000,
            min_df=1,  # Include rare terms
            ngram_range=(1, 2),  # Unigrams and bigrams
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

        print(f"[INFO] Computing cosine similarity matrix...")

        # Pre-compute full similarity matrix
        # Shape: [N, N] where N = number of movies
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)

        print(f"[INFO] Similarity engine initialized successfully")
        print(f"[INFO] Vocabulary size: {len(self.vectorizer.vocabulary_)}")

    def more_like_this(
        self,
        movie_id: int,
        limit: int = 12,
        min_similarity: float = 0.0,
    ) -> List[MovieRecord]:
        """
        Find movies most similar to the given movie_id.

        Args:
            movie_id: ID of the reference movie
            limit: Maximum number of similar movies to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            List of similar MovieRecord objects, sorted by similarity (descending)

        Note:
            - Returns empty list if movie_id not found
            - Similar movies can come from ANY source_db
            - Excludes the reference movie itself from results
        """
        idx = self.id_to_index.get(movie_id)

        if idx is None:
            print(f"[WARN] Movie ID {movie_id} not found in similarity engine")
            return []

        # Get similarity scores for this movie
        scores = list(enumerate(self.similarity_matrix[idx]))

        # Filter by minimum similarity threshold
        scores = [(i, score) for i, score in scores if score >= min_similarity]

        # Sort by similarity (descending)
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Skip first result (the movie itself, similarity=1.0)
        # Take next `limit` movies
        similar_indices = [i for i, _ in scores[1:limit + 1]]

        similar_movies = [self.movies[i] for i in similar_indices]

        if similar_movies:
            print(
                f"[INFO] Found {len(similar_movies)} similar movies for movie_id={movie_id} "
                f"('{self.movies[idx].title}')"
            )

        return similar_movies

    def get_similarity_score(
        self,
        movie_id_1: int,
        movie_id_2: int,
    ) -> float:
        """
        Get the similarity score between two specific movies.

        Args:
            movie_id_1: First movie ID
            movie_id_2: Second movie ID

        Returns:
            Similarity score between 0.0 and 1.0, or 0.0 if either movie not found
        """
        idx1 = self.id_to_index.get(movie_id_1)
        idx2 = self.id_to_index.get(movie_id_2)

        if idx1 is None or idx2 is None:
            return 0.0

        return float(self.similarity_matrix[idx1, idx2])

    def batch_more_like_this(
        self,
        movie_ids: Sequence[int],
        limit: int = 12,
    ) -> List[MovieRecord]:
        """
        Find movies similar to ANY of the given movie IDs.
        Useful for "Continue Watching" or multi-movie recommendations.

        Args:
            movie_ids: List of reference movie IDs
            limit: Maximum number of similar movies to return

        Returns:
            Aggregated list of similar movies, deduplicated and ranked
        """
        if not movie_ids:
            return []

        # Get indices for all valid movie IDs
        valid_indices = [
            self.id_to_index[mid]
            for mid in movie_ids
            if mid in self.id_to_index
        ]

        if not valid_indices:
            print(f"[WARN] None of the provided movie IDs found in similarity engine")
            return []

        # Aggregate similarity scores across all reference movies
        # Use maximum similarity to any reference movie
        import numpy as np
        aggregated_scores = self.similarity_matrix[valid_indices].max(axis=0)

        # Get top similar movies
        scored_indices = list(enumerate(aggregated_scores))

        # Filter out the reference movies themselves
        scored_indices = [
            (i, score)
            for i, score in scored_indices
            if i not in valid_indices
        ]

        scored_indices = sorted(scored_indices, key=lambda x: x[1], reverse=True)

        top_indices = [i for i, _ in scored_indices[:limit]]

        return [self.movies[i] for i in top_indices]