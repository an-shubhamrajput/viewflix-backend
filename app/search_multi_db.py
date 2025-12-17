"""
Cross-database movie search utilities.

This module provides helpers to:
- Search for movies by title across all configured movie databases.
- Identify which database / genre a movie comes from.
- Return a normalized dictionary for each match.

DB credentials are read ONLY from environment variables via
`app.reco.db_connections`, and no passwords are ever logged.
"""

from __future__ import annotations

from typing import List, Dict, Any

from app.reco.db_connections import get_reco_database_names, connect_to_database


def search_movies_by_title(
    title_query: str,
    limit_per_db: int = 5,
    max_results: int = 30,
) -> List[Dict[str, Any]]:
    """
    Search for movies by title across all configured movie databases.

    Strategy:
    - Use RECO_MOVIE_DATABASES (or DB_BY_GENRE fallback) to get database list.
    - For each database:
        * Try searching the `free_movies` table first.
        * If `free_movies` doesn't exist or yields no rows, fall back to
          the `popularmovies` table.
    - Aggregate results, tag each with source_db and genre_id, and
      sort globally by popularity descending.

    The function is read-only and safe to use in API handlers.
    """
    db_names = get_reco_database_names()
    title_pattern = f"%{title_query.strip()}%"

    all_rows: List[Dict[str, Any]] = []

    for db_name in db_names:
        def _run_query(table: str) -> List[Dict[str, Any]]:
            """
            Helper to run a title LIKE search against a specific table
            in the given database.
            """
            conn = connect_to_database(db_name)
            try:
                cursor = conn.cursor(dictionary=True)
                query = (
                    f"SELECT id, title, "
                    f"       COALESCE(genre_text, genre_ids) AS genre_text, "
                    f"       popularity, poster_path, release_date "
                    f"FROM {table} "
                    f"WHERE title LIKE %s "
                    f"ORDER BY popularity DESC "
                    f"LIMIT {limit_per_db}"
                )
                cursor.execute(query, (title_pattern,))
                return cursor.fetchall()
            finally:
                conn.close()

        # 1) Try free_movies first
        rows: List[Dict[str, Any]] = []
        source_table = None
        try:
            rows = _run_query("free_movies")
            source_table = "free_movies"
        except Exception as exc:
            # Table might not exist or schema might differ; log minimally and try fallback.
            print(
                f"[WARN] Search on 'free_movies' in '{db_name}' failed "
                f"(will try 'popularmovies'): {exc}"
            )
            rows = []

        # 2) Fallback to popularmovies if needed
        if not rows:
            try:
                rows = _run_query("popularmovies")
                source_table = "popularmovies"
            except Exception as exc:
                print(
                    f"[WARN] Search on 'popularmovies' in '{db_name}' failed: {exc}"
                )
                rows = []

        for row in rows:
            all_rows.append(
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "genre_text": row.get("genre_text"),
                    "popularity": row.get("popularity"),
                    "poster_path": row.get("poster_path"),
                    "release_date": row.get("release_date"),
                    "source_db": db_name,
                    "source_table": source_table,
                }
            )

    # Sort globally by popularity (descending), handling NULL/None as 0.
    def _pop_score(r: Dict[str, Any]) -> float:
        try:
            return float(r.get("popularity") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    all_rows_sorted = sorted(all_rows, key=_pop_score, reverse=True)
    return all_rows_sorted[:max_results]
