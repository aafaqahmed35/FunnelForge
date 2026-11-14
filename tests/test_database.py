"""Unit tests for database connection and schema initialization using mocks."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from psycopg import errors

from funnelforge.config import DatabaseConfig
from funnelforge.database import (
    DatabaseConnectionError,
    DatabaseError,
    get_connection,
    initialize_schema,
)


def test_get_connection_success():
    """Verify get_connection opens and properly closes connection in context."""
    mock_conn = MagicMock()
    mock_conn.closed = False

    with patch("psycopg.connect", return_value=mock_conn) as mock_connect:
        cfg = DatabaseConfig(host="localhost", port=5432, name="testdb", user="usr", password="pwd")
        with get_connection(cfg) as conn:
            assert conn is mock_conn
        
        mock_connect.assert_called_once_with(
            host="localhost", port=5432, dbname="testdb", user="usr", password="pwd"
        )
        mock_conn.close.assert_called_once()


def test_get_connection_with_url():
    """Verify psycopg.connect is called with connection URL if set."""
    mock_conn = MagicMock()
    mock_conn.closed = False
    url = "postgresql://user:pass@host:5432/dbname"

    with patch("psycopg.connect", return_value=mock_conn) as mock_connect:
        cfg = DatabaseConfig(database_url=url)
        with get_connection(cfg) as conn:
            assert conn is mock_conn
        mock_connect.assert_called_once_with(url)


def test_get_connection_failure():
    """Verify DatabaseConnectionError is raised when psycopg.connect fails."""
    with patch("psycopg.connect", side_effect=errors.OperationalError("Connection refused")):
        with pytest.raises(DatabaseConnectionError, match="Failed to connect to PostgreSQL"):
            with get_connection():
                pass


def test_get_connection_rollback_on_exception():
    """Verify connection rolls back on exception before closing."""
    mock_conn = MagicMock()
    mock_conn.closed = False

    with patch("psycopg.connect", return_value=mock_conn):
        with pytest.raises(RuntimeError, match="Application error"):
            with get_connection():
                raise RuntimeError("Application error")

        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()


def test_initialize_schema_success(tmp_path: Path):
    """Verify initialize_schema reads the SQL file and executes it on cursor."""
    schema_file = tmp_path / "test_schema.sql"
    sql_content = "CREATE TABLE test_table (id INT PRIMARY KEY);"
    schema_file.write_text(sql_content, encoding="utf-8")

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.database.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        initialize_schema(schema_path=schema_file)

        mock_cursor.execute.assert_called_once_with(sql_content)
        mock_conn.commit.assert_called_once()


def test_initialize_schema_missing_file(tmp_path: Path):
    """Verify initialize_schema raises FileNotFoundError when schema file is missing."""
    missing = tmp_path / "nonexistent.sql"
    with pytest.raises(FileNotFoundError, match="Schema file not found"):
        initialize_schema(schema_path=missing)


def test_initialize_schema_sql_error(tmp_path: Path):
    """Verify initialize_schema rolls back and raises DatabaseError on syntax/DDL error."""
    schema_file = tmp_path / "invalid.sql"
    schema_file.write_text("INVALID SQL", encoding="utf-8")

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = errors.SyntaxError("syntax error at or near INVALID")
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.database.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        with pytest.raises(DatabaseError, match="Failed to execute schema initialization SQL"):
            initialize_schema(schema_path=schema_file)

        mock_conn.rollback.assert_called_once()
