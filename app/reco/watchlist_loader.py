from dataclasses import dataclass
from typing import List
import os
import mysql.connector
from mysql.connector import Error

@dataclass
class WatchlistRecord:
    id: int
    movieId: int
    userId: float
    title: str
    poster_path: str
    movie_type: str
    watched: int
    original_title: str
    source_db: str


def load_watchlist_multi_db() -> List[WatchlistRecord]:
    """
    Load watchlists records from all databases listed in RECO_MOVIE_DATABASES.
    Safely skips:
      - missing databases
      - missing watchlists tables
    """
    records: List[WatchlistRecord] = []

    dbs = os.getenv("RECO_MOVIE_DATABASES", "")
    db_list = [db.strip() for db in dbs.split(",") if db.strip()]

    for db_name in db_list:
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=db_name,
            )

            cursor = conn.cursor(dictionary=True)

            cursor.execute("SHOW TABLES LIKE 'watchlists'")
            if not cursor.fetchone():
                print(f"[SKIP] watchlists table not found in '{db_name}'")
                continue

            cursor.execute("""
                SELECT
                    id,
                    movieId,
                    userId,
                    title,
                    poster_path,
                    movie_type,
                    watched,
                    original_title
                FROM watchlists
            """)

            rows = cursor.fetchall()

            for row in rows:
                records.append(
                    WatchlistRecord(
                        id=row["id"],
                        movieId=row["movieId"],
                        userId=row["userId"],
                        title=row["title"],
                        poster_path=row["poster_path"],
                        movie_type=row["movie_type"],
                        watched=row["watched"],
                        original_title=row["original_title"],
                        source_db=db_name,
                    )
                )

            print(f"[OK] Loaded {len(rows)} watchlists rows from '{db_name}'")

        except Error as e:
            print(f"[SKIP] Cannot load watchlists from '{db_name}': {e}")

        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    return records
