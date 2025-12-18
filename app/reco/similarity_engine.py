from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MovieSimilarityEngine:
    def __init__(self, movies):
        self.movies = movies
        self.id_to_index = {m.id: i for i, m in enumerate(movies)}

        self.corpus = [
            f"{m.genres} {m.overview}"
            for m in movies
        ]

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=8000
        )
        self.matrix = self.vectorizer.fit_transform(self.corpus)
        self.similarity = cosine_similarity(self.matrix)

    def more_like_this(self, movie_id, limit=12):
        idx = self.id_to_index.get(movie_id)
        if idx is None:
            return []

        scores = list(enumerate(self.similarity[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        indices = [i for i, _ in scores[1:limit + 1]]
        print(f"[INFO] Similarity engine initialized with {len(movies)} movies.")

        return [self.movies[i] for i in indices]
