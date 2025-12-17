# """
# Data loading utilities for the content-based recommender.

# This module reads movie metadata from MySQL using the same
# environment variables as the Flask app (`DB_HOST`, `DB_USER`,
# `DB_PASSWORD`, `DB_DATABASE`).

# Expected logical schema (can be mapped to any real table via config):

# movies (
#     id            INT / BIGINT,
#     title         VARCHAR,
#     genre_text    VARCHAR,  -- e.g. "Action|Drama|Thriller"
#     popularity    FLOAT / VARCHAR,
#     release_date  DATE or VARCHAR(10) in "YYYY-MM-DD"
# )
# """

# from __future__ import annotations

# import os
# from dataclasses import dataclass
# from datetime import date, datetime
# from typing import List, Dict, Any, Optional

# import mysql.connector


# @dataclass
# class MovieRecord:
#     """Lightweight container for the minimal metadata we need."""

#     id: int
#     title: str
#     genre_text: str
#     popularity_raw: float
#     release_date: Optional[date]
#     # Optional fields for richer use-cases (e.g. multi-DB training/inference)
#     poster_path: Optional[str] = None
#     source_db: Optional[str] = None


# @dataclass
# class MovieTableConfig:
#     """
#     Configuration describing where to read movie metadata from.

#     This lets us map different physical tables that match the logical
#     `movies` schema described in the requirements.
#     """

#     table_name: str = "movie_tamil_en"
#     id_column: str = "id"
#     title_column: str = "title"
#     genre_text_column: str = "genre_text"
#     popularity_column: str = "popularity"
#     release_date_column: str = "release_date"
#     poster_path_column: str = "poster_path"


# def _connect() -> mysql.connector.connection.MySQLConnection:
#     """
#     Create a direct MySQL connection using the same env vars as the Flask app.
#     """
#     host = os.environ.get("DB_HOST")
#     user = os.environ.get("DB_USER")
#     password = os.environ.get("DB_PASSWORD")
#     database = os.environ.get("DB_DATABASE")
#     port = int(os.environ.get("DB_PORT", "3306"))

#     if not all([host, user, password, database]):
#         raise RuntimeError(
#             "Database environment variables DB_HOST, DB_USER, "
#             "DB_PASSWORD, DB_DATABASE must be set."
#         )

#     return mysql.connector.connect(
#         host=host,
#         user=user,
#         password=password,
#         database=database,
#         port=port,
#     )


# def _parse_release_date(value: Any) -> Optional[date]:
#     """
#     Parse a release_date that might be stored as DATE, DATETIME or string.
#     Returns a `date` object or None if parsing fails.
#     """
#     if value is None:
#         return None
#     if isinstance(value, date):
#         return value
#     if isinstance(value, datetime):
#         return value.date()
#     if isinstance(value, str):
#         # Expecting "YYYY-MM-DD"
#         try:
#             return datetime.strptime(value[:10], "%Y-%m-%d").date()
#         except ValueError:
#             return None
#     return None


# def _to_float(value: Any) -> Optional[float]:
#     """
#     Safely cast numeric-like values to float.
#     """
#     if value is None:
#         return None
#     if isinstance(value, (int, float)):
#         return float(value)
#     try:
#         return float(str(value))
#     except (TypeError, ValueError):
#         return None


# def load_movies(config: MovieTableConfig) -> List[MovieRecord]:
#     """
#     Load movie metadata from MySQL.

#     This function only pulls the columns needed for the recommender.
#     """
#     conn = _connect()
#     try:
#         cursor = conn.cursor(dictionary=True)
#         query = f"""
#             SELECT
#                 {config.id_column}          AS id,
#                 {config.title_column}       AS title,
#                 {config.genre_text_column}  AS genre_text,
#                 {config.popularity_column}  AS popularity,
#                 {config.release_date_column} AS release_date
#             FROM {config.table_name}
#             WHERE {config.genre_text_column} IS NOT NULL
#               AND {config.genre_text_column} != ''
#         """
#         cursor.execute(query)
#         rows: List[Dict[str, Any]] = cursor.fetchall()
#     finally:
#         conn.close()

#     movies: List[MovieRecord] = []
#     for row in rows:
#         popularity = _to_float(row.get("popularity"))
#         if popularity is None:
#             # Skip entries without a valid popularity value; they add noise.
#             continue
#         rd = _parse_release_date(row.get("release_date"))
#         movies.append(
#             MovieRecord(
#                 id=int(row["id"]),
#                 title=row["title"] or "",
#                 genre_text=row["genre_text"] or "",
#                 popularity_raw=popularity,
#                 release_date=rd,
#             )
#         )
#     return movies



"""
Data loading utilities for the content-based recommender.

This module reads movie metadata from MySQL using the same
environment variables as the Flask app (`DB_HOST`, `DB_USER`,
`DB_PASSWORD`, `DB_DATABASE`).

Source table: moviedetails
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
    popularity_raw: float
    release_date: Optional[date]
    poster_path: Optional[str] = None
    source_db: Optional[str] = None


@dataclass
class MovieTableConfig:
    """
    Mapping between logical movie fields and physical DB columns.
    """

    table_name: str = "moviedetails"
    id_column: str = "movie_id"
    title_column: str = "movie_name"
    genre_text_column: str = "genres"
    popularity_column: str = "view_count"
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
        raise RuntimeError(
            "DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE must be set"
        )

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

def load_movies(config: MovieTableConfig = MovieTableConfig()) -> List[MovieRecord]:
    """
    Load movie metadata from moviedetails table.
    """
    conn = _connect()
    try:
        cursor = conn.cursor(dictionary=True)
        query = f"""
            SELECT
                {config.id_column}          AS id,
                {config.title_column}       AS title,
                {config.genre_text_column}  AS genre_text,
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

        movies.append(
            MovieRecord(
                id=int(row["id"]),
                title=row.get("title") or "",
                genre_text=row.get("genre_text") or "",
                popularity_raw=popularity,
                release_date=_parse_release_date(row.get("release_date")),
                poster_path=row.get("poster_path"),
                source_db="moviedetails",
            )
        )

    return movies

if __name__ == "__main__":
    movies = load_movies()

    print(f"\n[INFO] Total movies loaded: {len(movies)}\n")

    for i, movie in enumerate(movies[:10]):  # print only first 10
        print(
            f"{i+1}. ID={movie.id}, "
            f"Title='{movie.title}', "
            f"Genres='{movie.genre_text}', "
            f"Popularity={movie.popularity_raw}, "
            f"ReleaseDate={movie.release_date}, "
            f"Poster={movie.poster_path}"
        )
