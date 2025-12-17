"""
Multi-database data loading for the global content-based recommender.

This module:
- Connects to multiple MySQL databases using shared credentials.
- Discovers movie tables and their schemas dynamically.
- Reads movie rows from those tables.
- Attaches `source_db` to each record so we can track origin.

Design notes:
- We avoid hardcoding database names or table names.
- We prefer a standard table `free_movies` when present (per product spec),
  but we still *validate* its schema via DESCRIBE before using it.
- If `free_movies` is missing or contains no usable rows, we gracefully
  fall back to `popularmovies` where possible.
"""

from __future__ import annotations

from typing import List, Sequence, Dict, Any, Optional

from .db_connections import connect_to_database
from .data_loader import MovieTableConfig, MovieRecord, _parse_release_date, _to_float


def _list_tables(conn, database_name: str) -> List[str]:
    """
    Run `SHOW TABLES` in the given database.
    """
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    rows = cursor.fetchall()

    # MySQL returns rows like ('table_name',)
    tables = [row[0] for row in rows]
    print(f"[INFO] Tables in database '{database_name}': {tables}")
    return tables


def _describe_table(conn, table_name: str) -> List[Dict[str, Any]]:
    """
    Run `DESCRIBE table_name` and return a list of column metadata dictionaries.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"DESCRIBE {table_name}")
    rows: List[Dict[str, Any]] = cursor.fetchall()
    print(f"[INFO] Schema for '{table_name}': {[r['Field'] for r in rows]}")
    return rows


def _infer_movie_table_config(
    database_name: str,
    tables: Sequence[str],
    conn,
) -> Optional[MovieTableConfig]:
    """
    Inspect tables and infer which one contains movie data and how to map
    its columns to the logical movie schema, for the primary choice: `free_movies`.

    Strategy:
    - Prefer a table literally named `free_movies` when present (per product spec).
    - Validate its schema by checking for required logical fields.
    """
    # Prefer the canonical free_movies table when present.
    preferred_table = None
    if "free_movies" in tables:
        preferred_table = "free_movies"

    if not preferred_table:
        print(
            f"[WARN] No 'free_movies' table found in database '{database_name}'. "
            f"Skipping free_movies in this database (may fall back to other tables)."
        )
        return None

    cols = _describe_table(conn, preferred_table)
    col_names = {c["Field"] for c in cols}

    required_cols = {
        "id",
        "title",
        "genre_text",
        "popularity",
        "release_date",
    }

    missing = required_cols - col_names
    if missing:
        print(
            f"[WARN] Table '{preferred_table}' in database '{database_name}' "
            f"is missing required columns {missing}. Skipping this database."
        )
        return None

    # poster_path is optional; only use it if present.
    poster_col = "poster_path" if "poster_path" in col_names else None

    cfg = MovieTableConfig(
        table_name=preferred_table,
        id_column="id",
        title_column="title",
        genre_text_column="genre_text",
        popularity_column="popularity",
        release_date_column="release_date",
        poster_path_column=poster_col or "poster_path",
    )

    print(
        f"[INFO] Using table '{preferred_table}' in database '{database_name}' "
        f"with columns: id='{cfg.id_column}', title='{cfg.title_column}', "
        f"genre='{cfg.genre_text_column}', popularity='{cfg.popularity_column}', "
        f"release_date='{cfg.release_date_column}', poster='{poster_col}'."
    )
    return cfg


def _infer_popularmovies_config(
    database_name: str,
    tables: Sequence[str],
    conn,
) -> Optional[MovieTableConfig]:
    """
    Fallback: infer a MovieTableConfig for `popularmovies` if `free_movies`
    is unavailable or unusable.

    We accept either:
    - genre_text column, or
    - genre_ids column (treated as genre tokens).
    """
    if "popularmovies" not in tables:
        print(
            f"[WARN] No 'popularmovies' table found in database '{database_name}'. "
            f"Skipping popularmovies fallback."
        )
        return None

    cols = _describe_table(conn, "popularmovies")
    col_names = {c["Field"] for c in cols}

    required = {"id", "title", "popularity", "release_date"}
    missing = required - col_names
    if missing:
        print(
            f"[WARN] Table 'popularmovies' in database '{database_name}' "
            f"is missing required columns {missing}. Skipping this table."
        )
        return None

    # Choose a genre column: prefer human-readable genre_text if present,
    # otherwise fall back to numeric genre_ids.
    genre_col: Optional[str] = None
    if "genre_text" in col_names:
        genre_col = "genre_text"
    elif "genre_ids" in col_names:
        genre_col = "genre_ids"

    if genre_col is None:
        print(
            f"[WARN] Table 'popularmovies' in database '{database_name}' has no "
            f"'genre_text' or 'genre_ids' column. Skipping this table."
        )
        return None

    poster_col = "poster_path" if "poster_path" in col_names else None

    cfg = MovieTableConfig(
        table_name="popularmovies",
        id_column="id",
        title_column="title",
        genre_text_column=genre_col,
        popularity_column="popularity",
        release_date_column="release_date",
        poster_path_column=poster_col or "poster_path",
    )

    print(
        f"[INFO] Using table 'popularmovies' in database '{database_name}' "
        f"with columns: id='{cfg.id_column}', title='{cfg.title_column}', "
        f"genre='{cfg.genre_text_column}', popularity='{cfg.popularity_column}', "
        f"release_date='{cfg.release_date_column}', poster='{poster_col}'."
    )
    return cfg


def _load_movies_from_table(
    database_name: str,
    config: MovieTableConfig,
) -> List[MovieRecord]:
    """
    Load movie metadata from a specific database/table using an inferred config.
    """
    conn = connect_to_database(database_name)
    try:
        cursor = conn.cursor(dictionary=True)
        query = f"""
            SELECT
                {config.id_column}           AS id,
                {config.title_column}        AS title,
                {config.genre_text_column}   AS genre_text,
                {config.popularity_column}   AS popularity,
                {config.release_date_column} AS release_date
                {',' if config.poster_path_column else ''}
                {config.poster_path_column if config.poster_path_column else ''}
            FROM {config.table_name}
            WHERE {config.genre_text_column} IS NOT NULL
              AND {config.genre_text_column} != ''
        """
        cursor.execute(query)
        rows: List[Dict[str, Any]] = cursor.fetchall()
    finally:
        conn.close()

    print(
        f"[INFO] Fetched {len(rows)} raw rows from "
        f"'{database_name}.{config.table_name}'."
    )

    movies: List[MovieRecord] = []
    for row in rows:
        popularity = _to_float(row.get("popularity"))
        if popularity is None:
            # Skip entries without a valid popularity value; they add noise.
            continue
        release_date = _parse_release_date(row.get("release_date"))
        movies.append(
            MovieRecord(
                id=int(row["id"]),
                title=row.get("title") or "",
                genre_text=row.get("genre_text") or "",
                popularity_raw=popularity,
                release_date=release_date,
                poster_path=row.get("poster_path") if "poster_path" in row else None,
                source_db=database_name,
            )
        )

    print(
        f"[INFO] Accepted {len(movies)} movies after validation from "
        f"'{database_name}.{config.table_name}'."
    )
    return movies


def load_movies_multi_db(
    database_names: Sequence[str],
) -> List[MovieRecord]:
    """
    Load and combine movie metadata from multiple databases.
    """
    all_movies: List[MovieRecord] = []
    for db_name in database_names:
        print(f"[INFO] Inspecting database '{db_name}' for movie tables...")
        conn = None
        try:
            # Open connection to this specific database using shared creds.
            conn = connect_to_database(db_name)
            tables = _list_tables(conn, db_name)

            # First, try free_movies as the primary source.
            cfg_free = _infer_movie_table_config(db_name, tables, conn)

            # If no free_movies config, try popularmovies directly.
            if cfg_free is None:
                cfg_pop = _infer_popularmovies_config(db_name, tables, conn)
                cfg_to_use = cfg_pop
            else:
                cfg_to_use = cfg_free
        except Exception as exc:
            # Connection or inspection failure: log and skip this database.
            print(
                f"[WARN] Skipping database '{db_name}' due to connection/inspection error: {exc}"
            )
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            continue
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        if cfg_to_use is None:
            # Already logged why this DB was skipped.
            continue

        # 1) Attempt to load from the chosen config (free_movies if available, else popularmovies).
        try:
            movies = _load_movies_from_table(db_name, cfg_to_use)
        except Exception as exc:
            print(
                f"[WARN] Failed to load movies from '{db_name}.{cfg_to_use.table_name}': {exc}"
            )
            continue

        # 2) If free_movies yielded zero movies, try falling back to popularmovies.
        if not movies and cfg_to_use.table_name == "free_movies":
            print(
                f"[INFO] No usable movies found in '{db_name}.free_movies'. "
                f"Attempting fallback to 'popularmovies'."
            )
            # Need a fresh connection for schema inspection
            conn = None
            try:
                conn = connect_to_database(db_name)
                tables = _list_tables(conn, db_name)
                cfg_pop = _infer_popularmovies_config(db_name, tables, conn)
            except Exception as exc:
                print(
                    f"[WARN] Fallback inspection for 'popularmovies' in database "
                    f"'{db_name}' failed: {exc}"
                )
                cfg_pop = None
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

            if cfg_pop is not None:
                try:
                    movies = _load_movies_from_table(db_name, cfg_pop)
                except Exception as exc:
                    print(
                        f"[WARN] Failed to load movies from fallback "
                        f"'{db_name}.{cfg_pop.table_name}': {exc}"
                    )
                    movies = []

        all_movies.extend(movies)

    print(f"[INFO] Total movies loaded across all databases: {len(all_movies)}")
    return all_movies



