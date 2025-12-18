"""
Multi-database data loading for the global content-based recommender.

This module:
- Connects to multiple MySQL databases using shared credentials.
- Loads movies ONLY from the `moviedetails` table.
- Attaches `source_db` to each record for tracking origin.

CRITICAL RULES:
- ONLY load from `moviedetails` table
- NO fallback to free_movies, popularmovies, or any other tables
- Every movie must have source_db set
"""

from __future__ import annotations

from typing import List, Sequence, Dict, Any

from .db_connections import connect_to_database, get_reco_database_names
from .data_loader import MovieTableConfig, MovieRecord, _parse_release_date, _to_float


def _table_exists(conn, table_name: str) -> bool:
    """
    Check if a specific table exists in the connected database.
    """
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    rows = cursor.fetchall()
    tables = [row[0] for row in rows]
    return table_name in tables


def _describe_table(conn, table_name: str) -> List[Dict[str, Any]]:
    """
    Run `DESCRIBE table_name` and return column metadata.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"DESCRIBE {table_name}")
    rows: List[Dict[str, Any]] = cursor.fetchall()
    return rows


def _validate_moviedetails_schema(
    database_name: str,
    conn,
) -> bool:
    """
    Validate that moviedetails table exists and has required columns.

    Required columns:
    - id
    - title
    - genres
    - overview (can be NULL)
    - popularity
    - release_date
    - poster_path
    """
    if not _table_exists(conn, "moviedetails"):
        print(f"[WARN] Table 'moviedetails' not found in database '{database_name}'")
        return False

    cols = _describe_table(conn, "moviedetails")
    col_names = {c["Field"] for c in cols}

    # Updated required columns (removed 'status' since your table doesn't have it)
    required_cols = {
        "id",
        "title",
        "genres",
        "overview",
        "popularity",
        "release_date",
        "poster_path",
    }

    missing = required_cols - col_names
    if missing:
        print(
            f"[WARN] Table 'moviedetails' in database '{database_name}' "
            f"is missing required columns: {missing}"
        )
        return False

    print(f"[INFO] Table 'moviedetails' in database '{database_name}' validated successfully")
    return True


def _load_movies_from_moviedetails(
    database_name: str,
) -> List[MovieRecord]:
    """
    Load movie metadata from the moviedetails table in the specified database.

    STRICT: Only loads from moviedetails, no fallback tables.
    """
    conn = connect_to_database(database_name)
    try:
        # Validate schema first
        if not _validate_moviedetails_schema(database_name, conn):
            print(f"[WARN] Skipping database '{database_name}' due to schema validation failure")
            return []

        cursor = conn.cursor(dictionary=True)

        # Updated query: removed status filter since your table doesn't have that column
        query = """
            SELECT
                id,
                title,
                genres AS genre_text,
                overview,
                popularity,
                release_date,
                poster_path
            FROM moviedetails
            WHERE genres IS NOT NULL
              AND genres != ''
              AND genres != '[]'
        """
        cursor.execute(query)
        rows: List[Dict[str, Any]] = cursor.fetchall()

        print(f"[INFO] Fetched {len(rows)} raw rows from '{database_name}.moviedetails'")
    except Exception as exc:
        print(f"[ERROR] Failed to query '{database_name}.moviedetails': {exc}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

    movies: List[MovieRecord] = []
    for row in rows:
        popularity = _to_float(row.get("popularity"))
        if popularity is None or popularity == 0:
            # Skip movies with no popularity
            continue

        # MANDATORY: overview must not be None
        overview = row.get("overview")
        if overview is None:
            overview = ""

        release_date = _parse_release_date(row.get("release_date"))

        movies.append(
            MovieRecord(
                id=int(row["id"]),
                title=row.get("title") or "",
                genre_text=row.get("genre_text") or "",
                overview=overview,
                popularity_raw=popularity,
                release_date=release_date,
                poster_path=row.get("poster_path"),
                source_db=database_name,  # CRITICAL: Track origin
            )
        )

    print(f"[INFO] Accepted {len(movies)} valid movies from '{database_name}.moviedetails'")
    return movies


def load_movies_multi_db(
    database_names: Sequence[str] | None = None,
) -> List[MovieRecord]:
    """
    Load and combine movie metadata from multiple databases.

    Args:
        database_names: List of database names to query. If None, auto-discovers
                       from environment or genre_config.

    Returns:
        Combined list of MovieRecord objects, each tagged with source_db.

    STRICT BEHAVIOR:
    - Only loads from moviedetails table
    - No fallback to other tables
    - Skips databases without valid moviedetails table
    """
    if database_names is None:
        database_names = get_reco_database_names()

    print(f"[INFO] Loading movies from {len(database_names)} databases...")

    all_movies: List[MovieRecord] = []
    successful_dbs = 0
    failed_dbs = []

    for db_name in database_names:
        print(f"\n[INFO] Processing database '{db_name}'...")

        try:
            movies = _load_movies_from_moviedetails(db_name)
            if movies:
                all_movies.extend(movies)
                successful_dbs += 1
            else:
                failed_dbs.append(db_name)
        except Exception as exc:
            print(f"[ERROR] Failed to load from database '{db_name}': {exc}")
            failed_dbs.append(db_name)
            continue

    print(f"\n{'=' * 70}")
    print(f"[SUCCESS] Total movies loaded: {len(all_movies)}")
    print(f"[INFO] Successful databases: {successful_dbs}/{len(database_names)}")
    if failed_dbs:
        print(f"[WARN] Failed databases ({len(failed_dbs)}): {', '.join(failed_dbs[:5])}")
        if len(failed_dbs) > 5:
            print(f"       ... and {len(failed_dbs) - 5} more")

    # Summary by source
    if all_movies:
        source_counts = {}
        for movie in all_movies:
            source_counts[movie.source_db] = source_counts.get(movie.source_db, 0) + 1

        print(f"\n[INFO] Movies by source database:")
        for source, count in sorted(source_counts.items()):
            print(f"  - {source}: {count} movies")
    print("=" * 70)

    return all_movies