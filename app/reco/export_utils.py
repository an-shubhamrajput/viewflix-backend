import csv
from pathlib import Path
from typing import Sequence

from .data_loader import MovieRecord
from .preprocessing import EngineeredFeatures


def export_preprocessed_movies_csv(
    movies: Sequence[MovieRecord],
    engineered: EngineeredFeatures,
    output_path: str | Path,
) -> None:
    """
    Export preprocessed movie features to CSV.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    genre_names = list(engineered.genre_vocab.keys())

    with output_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        header = [
            "movie_id",
            "title",
            "genres",
            "popularity_norm",
            "recency_score",
        ] + genre_names

        writer.writerow(header)

        # Rows
        for i, movie in enumerate(movies):
            row = [
                movie.id,
                movie.title,
                movie.genre_text,
                float(engineered.popularity_norm[i, 0]),
                float(engineered.recency_scores[i, 0]),
            ] + engineered.movie_genre_vectors[i].astype(int).tolist()

            writer.writerow(row)

    print(f"[SUCCESS] CSV exported → {output_path}")
    print(f"[INFO] Movies: {len(movies)}, Genres: {len(genre_names)}")
