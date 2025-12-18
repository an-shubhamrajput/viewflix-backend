import csv
from pathlib import Path

from .preprocessing import EngineeredFeatures


# def export_preprocessed_movies_csv(
#     engineered: EngineeredFeatures,
#     output_path: str | Path,
# ) -> None:
#     """
#     Export preprocessed movie features to CSV.
#     """
#     output_path = Path(output_path)
#     output_path.parent.mkdir(parents=True, exist_ok=True)

#     # Stable genre column names
#     genre_cols = [f"genre_{g}" for g in engineered.genre_vocab.keys()]

#     with output_path.open(mode="w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)

#         # Header
#         writer.writerow(
#             [
#                 "movie_id",
#                 "title",
#                 "overview",
#                 "popularity_norm",
#                 "recency_score",
#                 *genre_cols,
#             ]
#         )

#         # Rows
#         for i in range(len(engineered.movie_ids)):
#             writer.writerow(
#                 [
#                     int(engineered.movie_ids[i]),
#                     engineered.titles[i],
#                     engineered.overviews[i],
#                     float(engineered.popularity_norm[i, 0]),
#                     float(engineered.recency_scores[i, 0]),
#                     *engineered.movie_genre_vectors[i].astype(int).tolist(),
#                 ]
#             )

#     print(f"✅ CSV exported → {output_path}")
#     print(
#         f"📊 Movies: {len(engineered.movie_ids)}, "
#         f"Genres: {len(genre_cols)}"
#     )
