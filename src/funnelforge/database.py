"""Database connectivity and schema initialization using psycopg."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import psycopg
from psycopg import Connection, errors

from funnelforge.config import DatabaseConfig, PROJECT_ROOT

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception raised when a database operation fails."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when connecting to PostgreSQL fails."""
    pass


@contextmanager
def get_connection(config: Optional[DatabaseConfig] = None) -> Generator[Connection, None, None]:
    """Provide a transactional PostgreSQL connection context manager.

    Closes the connection upon exiting the context.
    Rolls back any uncommitted transaction if an exception occurs.
    """
    cfg = config or DatabaseConfig.from_env()
    conn: Optional[Connection] = None

    try:
        if cfg.database_url:
            conn = psycopg.connect(cfg.database_url)
        else:
            conn = psycopg.connect(**cfg.to_connection_params())
    except errors.Error as err:
        msg = f"Failed to connect to PostgreSQL at {cfg.host}:{cfg.port}/{cfg.name}: {err}"
        logger.error(msg)
        raise DatabaseConnectionError(msg) from err
    except Exception as err:
        msg = f"Unexpected error while connecting to PostgreSQL: {err}"
        logger.error(msg)
        raise DatabaseConnectionError(msg) from err

    try:
        yield conn
    except Exception:
        if conn and not conn.closed:
            conn.rollback()
        raise
    finally:
        if conn and not conn.closed:
            conn.close()


def initialize_schema(
    schema_path: Optional[Path] = None,
    config: Optional[DatabaseConfig] = None,
) -> None:
    """Execute the DDL in schema.sql to create database tables and indexes safely.

    Schema initialization is idempotent.
    """
    path = schema_path or (PROJECT_ROOT / "sql" / "schema.sql")
    if not path.is_file():
        raise FileNotFoundError(f"Schema file not found at: {path}")

    sql_script = path.read_text(encoding="utf-8")

    with get_connection(config) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql_script)
                conn.commit()
                logger.info("Database schema initialized successfully from %s", path)
            except errors.Error as err:
                conn.rollback()
                msg = f"Failed to execute schema initialization SQL: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err


def initialize_p2_schema(
    schema_path: Optional[Path] = None,
    config: Optional[DatabaseConfig] = None,
) -> None:
    """Execute the DDL in p2_schema.sql to create processed tables and data_quality_issues.

    Initialization is idempotent.
    """
    path = schema_path or (PROJECT_ROOT / "sql" / "p2_schema.sql")
    if not path.is_file():
        raise FileNotFoundError(f"P2 Schema file not found at: {path}")

    sql_script = path.read_text(encoding="utf-8")

    with get_connection(config) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql_script)
                conn.commit()
                logger.info("P2 database schema initialized successfully from %s", path)
            except errors.Error as err:
                conn.rollback()
                msg = f"Failed to execute P2 schema initialization SQL: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err

