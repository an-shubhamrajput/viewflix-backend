import csv
from pathlib import Path
from typing import Sequence

from .watchlist_loader import WatchlistRecord


def export_watchlist_csv(
    records: Sequence[WatchlistRecord],
    output_path: str | Path,
) -> None:
    """
    Export user watchlist records to CSV with source_db tracking.
    """

    if not records:
        print("[WARN] No watchlist records to export")
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "movie_id",
        "user_id",
        "title",
        "original_title",
        "poster_path",
        "movie_type",
        "watched",
        "source_db",
    ]

    with output_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in records:
            writer.writerow(
                {
                    "id": r.id,
                    "movie_id": r.movieId,           # ✅ FIX
                    "user_id": r.userId,             # ✅ FIX
                    "title": r.title,
                    "original_title": r.original_title,
                    "poster_path": r.poster_path,
                    "movie_type": r.movie_type,
                    "watched": int(r.watched or 0),
                    "source_db": r.source_db,
                }
            )

    print(f"✅ Watchlist CSV exported → {output_path}")
    print(f"📊 Rows: {len(records)}")
