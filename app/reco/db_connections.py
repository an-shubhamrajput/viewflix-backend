"""
Database connection utilities for the multi-DB recommender.

Responsibilities:
- Read base connection settings from environment variables
  (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT).
- Discover which movie databases to use for training/inference.
- Provide helpers to open raw MySQL connections per database.

IMPORTANT:
- This module NEVER hardcodes credentials. Everything comes from env.
"""

from __future__ import annotations

import os
from typing import List

import mysql.connector


def get_base_connection_params() -> dict:
    """
    Read base MySQL connection parameters from environment variables.
    """
    host = os.environ.get("DB_HOST")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    port = int(os.environ.get("DB_PORT", "3306"))

    if not all([host, user, password]):
        raise RuntimeError(
            "Environment variables DB_HOST, DB_USER, DB_PASSWORD must be set "
            "for the recommender."
        )

    return {
        "host": host,
        "user": user,
        "password": password,
        "port": port,
    }


def _discover_all_databases() -> List[str]:
    """
    Run `SHOW DATABASES` using the shared connection settings.

    This is used only for schema discovery and logging; credentials are read
    exclusively from environment variables.
    """
    params = get_base_connection_params()
    conn = mysql.connector.connect(**params)
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        rows = cursor.fetchall()
    finally:
        conn.close()

    db_names = [row[0] for row in rows]
    print(f"[INFO] Databases discovered on server {params['host']}: {db_names}")
    return db_names


def get_reco_database_names() -> List[str]:
    """
    Determine which databases contain movie tables for the recommender.

    Priority:
    1. RECO_MOVIE_DATABASES (comma-separated list, trusted as-is; no SHOW DATABASES)
    2. Values from app.genre_config.DB_BY_GENRE (fallback, validated via SHOW DATABASES)
    """
    # 1) Prefer explicit configuration; avoid needing a privileged "admin" user.
    raw = os.environ.get("RECO_MOVIE_DATABASES")
    if raw:
        requested = [db.strip() for db in raw.split(",") if db.strip()]
        print(f"[INFO] Using databases from RECO_MOVIE_DATABASES (no SHOW DATABASES): {requested}")
        return requested

    # 2) Fallback: derive from existing genre configuration and validate using SHOW DATABASES
    available_dbs = set(_discover_all_databases())
    try:
        from app.genre_config import DB_BY_GENRE

        configured = sorted(set(DB_BY_GENRE.values()))
        selected = [db for db in configured if db in available_dbs]
        missing = [db for db in configured if db not in available_dbs]
        if missing:
            print(f"[WARN] Databases defined in genre_config.DB_BY_GENRE but not present on server: {missing}")
        if not selected:
            raise RuntimeError(
                "No movie databases found on the server from genre_config.DB_BY_GENRE. "
                "Either create the databases or set RECO_MOVIE_DATABASES explicitly."
            )
        print(f"[INFO] Using databases from genre_config.DB_BY_GENRE: {selected}")
        return selected
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise RuntimeError(
            "Failed to determine movie databases. "
            "Set RECO_MOVIE_DATABASES or ensure app.genre_config.DB_BY_GENRE exists."
        ) from exc


def connect_to_database(database_name: str) -> mysql.connector.connection.MySQLConnection:
    """
    Open a direct MySQL connection to the specified database.

    Credentials resolution order (no hardcoding):
    1. Per-database credentials from environment variables, if present:
       - If DB name ends with "_movies", e.g. "tamil_movies":
           DB_TAMIL_USER, DB_TAMIL_PASSWORD
       - Generic pattern based on full DB name:
           DB_TAMIL_MOVIES_USER, DB_TAMIL_MOVIES_PASSWORD
    2. Fallback to shared credentials:
       - DB_USER, DB_PASSWORD

    Host/port always come from:
       - DB_HOST, DB_PORT
    """
    base = get_base_connection_params()

    # Start with shared/default credentials
    user = base["user"]
    password = base["password"]

    # Derive candidate prefixes from the database name.
    candidates = []

    # If DB name ends with "_movies", e.g. "tamil_movies" -> prefix "TAMIL"
    if database_name.endswith("_movies"):
        short = database_name[: -len("_movies")].upper()
        if short:
            candidates.append(short)

    # Full DB name pattern, e.g. "tamil_movies" -> "TAMIL_MOVIES"
    full_key = "".join(ch if ch.isalnum() else "_" for ch in database_name.upper())
    if full_key:
        candidates.append(full_key)

    # Try per-database env vars in order of candidates.
    for prefix in candidates:
        env_user = os.environ.get(f"DB_{prefix}_USER")
        env_password = os.environ.get(f"DB_{prefix}_PASSWORD")
        if env_user and env_password:
            print(
                f"[INFO] Using per-database credentials from DB_{prefix}_USER/DB_{prefix}_PASSWORD "
                f"for database '{database_name}'."
            )
            user = env_user
            password = env_password
            break

    return mysql.connector.connect(
        host=base["host"],
        user=user,
        password=password,
        port=base["port"],
        database=database_name,
    )



