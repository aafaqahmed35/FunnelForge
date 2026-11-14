"""Unit tests for AnalyticsRepository using mocked database connection."""

from unittest.mock import MagicMock, patch

import pytest

from funnelforge.analytics_repository import AnalyticsRepository
from funnelforge.config import DatabaseConfig
from funnelforge.database import DatabaseError


def test_repository_campaign_performance():
    """Verify repository executes campaign_performance.sql query."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"campaign_id": "CMP-001", "campaign_name": "Test", "roas": 1.5}
    ]
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.analytics_repository.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        repo = AnalyticsRepository(config=DatabaseConfig())
        results = repo.get_campaign_performance()

        assert len(results) == 1
        assert results[0]["campaign_id"] == "CMP-001"
        assert results[0]["roas"] == 1.5
        mock_cursor.execute.assert_called_once()


def test_repository_conversion_funnel():
    """Verify repository executes conversion funnel query and returns dictionary."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            "total_impressions": 5000,
            "total_clicks": 1500,
            "total_conversions": 300,
            "impression_to_click_pct": 30.0,
            "click_to_conversion_pct": 20.0,
            "overall_conversion_pct": 6.0,
        }
    ]
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.analytics_repository.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        repo = AnalyticsRepository(config=DatabaseConfig())
        funnel = repo.get_conversion_funnel()

        assert funnel["total_impressions"] == 5000
        assert funnel["impression_to_click_pct"] == 30.0


def test_repository_empty_funnel_fallback():
    """Verify repository returns safe zeroed dict if funnel returns no rows."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.analytics_repository.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        repo = AnalyticsRepository(config=DatabaseConfig())
        funnel = repo.get_conversion_funnel()

        assert funnel["total_impressions"] == 0
        assert funnel["overall_conversion_pct"] == 0.0


def test_repository_database_error_handling():
    """Verify repository catches psycopg exceptions and raises DatabaseError."""
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = RuntimeError("Syntax error")
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.analytics_repository.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        repo = AnalyticsRepository(config=DatabaseConfig())
        with pytest.raises(DatabaseError, match="Analytics query execution failed"):
            repo.get_channel_performance()


def test_repository_missing_sql_file():
    """Verify repository raises FileNotFoundError if analytical query file is missing."""
    repo = AnalyticsRepository()
    with pytest.raises(FileNotFoundError, match="Analytics SQL file not found"):
        repo._read_sql_file("nonexistent_metric.sql")
