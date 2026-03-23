from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MovieSimilarityEngine:
    def __init__(self, movies):
        """
        Initialize the similarity engine with a list of movies.

        Args:
            movies: List of movie objects with attributes like id, genres, and overview.
        """
        self.movies = movies
        self.id_to_index = {m.id: i for i, m in enumerate(movies)}

        # Create a corpus combining genres and overviews for each movie
        self.corpus = [f"{m.genres} {m.overview}" for m in movies]

        # Initialize the TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=8000)
        self.matrix = self.vectorizer.fit_transform(self.corpus)

        # Compute cosine similarity between all movies
        self.similarity = cosine_similarity(self.matrix)

    def more_like_this(self, movie_id, limit=12):
        """
        Get movies similar to the given movie ID.

        Args:
            movie_id: The ID of the movie to find similar movies for.
            limit: The maximum number of similar movies to return.

        Returns:
            A list of movie objects similar to the given movie.
        """
        idx = self.id_to_index.get(movie_id)
        if idx is None:
            return []

        # Compute similarity scores for the given movie
        scores = list(enumerate(self.similarity[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Get the indices of the most similar movies
        indices = [i for i, _ in scores[1 : limit + 1]]
        print(f"[INFO] Similarity engine initialized with {len(self.movies)} movies.")

        return [self.movies[i] for i in indices]
