"""
Training script for the content-based movie recommender.

This script:
1. Loads movies from multiple databases (moviedetails table only)
2. Preprocesses and engineers features
3. Trains a Linear Regression model
4. Exports movie feature CSV (with source_db)
5. Exports unified user watchlists CSV (with source_db)
6. Saves the trained model and similarity engine
"""

from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import joblib

# --------------------------------------------------
# Environment & Path Setup
# --------------------------------------------------
load_dotenv()

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# --------------------------------------------------
# Imports
# --------------------------------------------------
try:
    from app.reco.multi_db_loader import load_movies_multi_db
    from app.reco.model import train_recommender, DEFAULT_MODEL_PATH
    from app.reco.preprocessing import export_movie_dataset_csv
    from app.reco.similarity import MovieSimilarityEngine
    from app.reco.watchlist_loader import load_watchlist_multi_db
    from app.reco.export_watchlist_csv import export_watchlist_csv
except ModuleNotFoundError as e:
    print(f"[ERROR] Import failed: {e}")
    print(f"[INFO] Python path: {sys.path}")
    sys.exit(1)


def main():
    print("=" * 70)
    print("CONTENT-BASED MOVIE RECOMMENDER TRAINING")
    print("=" * 70)

    # --------------------------------------------------
    # CONFIG
    # --------------------------------------------------
    print("\n[CONFIG]")
    print(f"  DB_HOST: {os.getenv('DB_HOST')}")
    print(f"  DB_USER: {os.getenv('DB_USER')}")

    reco_dbs = os.getenv("RECO_MOVIE_DATABASES", "")
    db_list = [db.strip() for db in reco_dbs.split(",") if db.strip()]

    if not db_list:
        print("[ERROR] RECO_MOVIE_DATABASES not set")
        sys.exit(1)

    print(f"  Databases ({len(db_list)}): {db_list}")

    # --------------------------------------------------
    # STEP 1: Load movies (multi DB)
    # --------------------------------------------------
    print("\n[STEP 1] Loading movies from multiple databases...")

    movies = load_movies_multi_db()

    if not movies:
        print("[ERROR] No movies loaded")
        sys.exit(1)

    print(f"[SUCCESS] Loaded {len(movies)} movies")

    # --------------------------------------------------
    # STEP 2: Default user profile
    # --------------------------------------------------
    print("\n[STEP 2] Defining default user profile...")

    default_user_genres = [
        # "Action",
        # "Comedy",
        # "Drama",
        # "Thriller",
        "Romance",
    ]

    print(f"  Genres: {default_user_genres}")

    # --------------------------------------------------
    # STEP 3: Train recommender
    # --------------------------------------------------
    print("\n[STEP 3] Training recommender model...")

    recommender, metrics = train_recommender(
        movies=movies,
        default_user_genres=default_user_genres,
        test_size=0.2,
        random_state=42,
    )

    print("[SUCCESS] Training completed")
    print(f"  MSE: {metrics['mse']:.6f}")
    print(f"  R² : {metrics['r2']:.6f}")

    # --------------------------------------------------
    # STEP 4: Export movie feature CSV
    # --------------------------------------------------
    print("\n[STEP 4] Exporting movie feature CSV...")

    movies_csv_path = (
        project_root / "app" / "reco_artifacts" / "movies_features.csv"
    )

    export_movie_dataset_csv(
        engineered=recommender.engineered,
        output_path=movies_csv_path,
    )

    # --------------------------------------------------
    # STEP 5: Export watchlists CSV (multi DB, safe)
    # --------------------------------------------------
    print("\n[STEP 5] Exporting unified user watchlists CSV...")

    watchlist_records = load_watchlist_multi_db()

    watchlist_csv_path = (
        project_root / "app" / "reco_artifacts" / "user_watchlist.csv"
    )

    export_watchlist_csv(
        records=watchlist_records,
        output_path=watchlist_csv_path,
    )

    # --------------------------------------------------
    # STEP 6: Save model
    # --------------------------------------------------
    print("\n[STEP 6] Saving trained model...")

    recommender.save(DEFAULT_MODEL_PATH)
    print(f"[SUCCESS] Model saved → {DEFAULT_MODEL_PATH}")

    # --------------------------------------------------
    # STEP 7: Build similarity engine
    # --------------------------------------------------
    print("\n[STEP 7] Building similarity engine...")

    similarity_engine = MovieSimilarityEngine(movies)
    similarity_path = Path(DEFAULT_MODEL_PATH).parent / "similarity_engine.joblib"
    joblib.dump(similarity_engine, similarity_path)

    print(f"[SUCCESS] Similarity engine saved → {similarity_path}")

    # --------------------------------------------------
    # STEP 8: Validation
    # --------------------------------------------------
    print("\n[STEP 8] Validation test")

    test_movie = movies[0]
    similar = similarity_engine.more_like_this(test_movie.id, limit=5)

    print(f"\nSimilar to '{test_movie.title}':")
    for i, movie in enumerate(similar, 1):
        print(f"  {i}. {movie.title} ({movie.source_db})")

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------
    print("\n" + "=" * 70)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(f"Movies CSV     : {movies_csv_path}")
    print(f"Watchlist CSV  : {watchlist_csv_path}")
    print(f"Model          : {DEFAULT_MODEL_PATH}")
    print(f"Similarity     : {similarity_path}")
    print(f"Total movies   : {len(movies)}")
    print(f"Watchlist rows : {len(watchlist_records)}")

    print("\n[READY] System ready for inference 🚀")


if __name__ == "__main__":
    main()
