"""
Data loading utilities for the content-based recommender.

This module reads movie metadata from MySQL using the same
environment variables as the Flask app (`DB_HOST`, `DB_USER`,
`DB_PASSWORD`, `DB_DATABASE`).

Source table: moviedetails (ONLY)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import mysql.connector


# -------------------------
# Data containers
# -------------------------


@dataclass
class MovieRecord:
    """Lightweight container for the minimal metadata we need."""

    id: int
    title: str
    genre_text: str
    overview: str
    popularity_raw: float
    release_date: Optional[date]
    poster_path: Optional[str]
    source_db: str  # MANDATORY: tracks which database this movie came from
    spoken_languages: str = ""


@dataclass
class MovieTableConfig:
    """
    Mapping between logical movie fields and physical DB columns.
    """

    table_name: str = "moviedetails"
    id_column: str = "id"
    title_column: str = "title"
    genre_text_column: str = "genres"
    overview_column: str = "overview"
    popularity_column: str = "popularity"
    release_date_column: str = "release_date"
    poster_path_column: str = "poster_path"
    status_column: str = "status"


# -------------------------
# DB connection helpers
# -------------------------


def _connect() -> mysql.connector.connection.MySQLConnection:
    host = os.environ.get("DB_HOST")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    database = os.environ.get("DB_DATABASE")
    port = int(os.environ.get("DB_PORT", "3306"))

    if not all([host, user, password, database]):
        raise RuntimeError("DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE must be set")

    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
    )


# -------------------------
# Parsing helpers
# -------------------------


def _parse_release_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


# -------------------------
# Core loader
# -------------------------


def load_movies(
    config: MovieTableConfig = MovieTableConfig(), source_db_name: str = "default"
) -> List[MovieRecord]:
    """
    Load movie metadata from moviedetails table.

    Args:
        config: Table configuration mapping
        source_db_name: Database identifier to tag each movie with
    """
    conn = _connect()
    try:
        cursor = conn.cursor(dictionary=True)
        query = f"""
            SELECT
                {config.id_column}          AS id,
                {config.title_column}       AS title,
                {config.genre_text_column}  AS genre_text,
                {config.overview_column}    AS overview,
                {config.popularity_column}  AS popularity,
                {config.release_date_column} AS release_date,
                {config.poster_path_column} AS poster_path
            FROM {config.table_name}
            WHERE {config.genre_text_column} IS NOT NULL
              AND {config.genre_text_column} != ''
              AND {config.status_column} = 'active'
        """
        cursor.execute(query)
        rows: List[Dict[str, Any]] = cursor.fetchall()
    finally:
        conn.close()

    movies: List[MovieRecord] = []
    for row in rows:
        popularity = _to_float(row.get("popularity"))
        if popularity is None:
            continue

        # MANDATORY: overview must not be None
        overview = row.get("overview") or ""

        movies.append(
            MovieRecord(
                id=int(row["id"]),
                title=row.get("title") or "",
                genre_text=row.get("genre_text") or "",
                overview=overview,
                popularity_raw=popularity,
                release_date=_parse_release_date(row.get("release_date")),
                poster_path=row.get("poster_path"),
                source_db=source_db_name,  # Track origin database
            )
        )

    return movies


if __name__ == "__main__":
    movies = load_movies()

    print(f"\n[INFO] Total movies loaded: {len(movies)}\n")

    for i, movie in enumerate(movies[:10]):
        print(
            f"{i+1}. ID={movie.id}, "
            f"Title='{movie.title}', "
            f"Overview='{movie.overview[:30]}...', "
            f"Genres='{movie.genre_text}', "
            f"Popularity={movie.popularity_raw}, "
            f"ReleaseDate={movie.release_date}, "
            f"Poster={movie.poster_path}, "
            f"SourceDB={movie.source_db}"
        )
