"""Unit tests for CSV ingestion and database loading using mocks."""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
import pandas as pd
import pytest
from psycopg import errors

from funnelforge.database import DatabaseError
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import (
    EXPECTED_COLUMNS,
    IngestionResult,
    ingest_data,
    prepare_records,
    validate_csv,
)


def test_validate_csv_success(tmp_path: Path):
    """Verify validate_csv returns valid dataframe when columns match."""
    csv_file = tmp_path / "campaigns.csv"
    data = {col: [1] for col in EXPECTED_COLUMNS["campaigns"]}
    pd.DataFrame(data).to_csv(csv_file, index=False)

    df = validate_csv(csv_file, "campaigns")
    assert list(df.columns) == EXPECTED_COLUMNS["campaigns"]


def test_validate_csv_missing_file(tmp_path: Path):
    """Verify validate_csv raises FileNotFoundError if file is missing."""
    missing = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError, match="Required CSV file missing"):
        validate_csv(missing, "campaigns")


def test_validate_csv_missing_columns(tmp_path: Path):
    """Verify validate_csv raises ValueError when required columns are absent."""
    csv_file = tmp_path / "customers.csv"
    df = pd.DataFrame({"customer_id": ["C1"], "customer_name": ["Alice"]})
    df.to_csv(csv_file, index=False)

    with pytest.raises(ValueError, match="missing expected columns"):
        validate_csv(csv_file, "customers")


def test_prepare_records_sanitizes_nan_to_none():
    """Verify prepare_records transforms NaN / float('nan') into Python None for SQL NULL."""
    df = pd.DataFrame({
        "event_id": ["EVT-1", "EVT-2"],
        "customer_id": ["C1", "C2"],
        "campaign_id": ["CMP-1", "CMP-2"],
        "event_type": ["impression", "conversion"],
        "event_timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
        "revenue": [np.nan, 99.50],
    })
    records = prepare_records(df, EXPECTED_COLUMNS["events"])
    assert len(records) == 2
    assert records[0][5] is None
    assert records[1][5] == 99.50


def test_ingest_data_mocked_success(tmp_path: Path):
    """Verify transactional bulk loading of all three datasets with mocked DB connection."""
    # Generate real CSV datasets into tmp_path
    generate_all_datasets(tmp_path, seed=42)

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.ingestion.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = ingest_data(data_dir=tmp_path)

        assert isinstance(result, IngestionResult)
        assert result.records_loaded["raw_campaigns"] == 20
        assert result.records_loaded["raw_customers"] == 1000
        assert result.records_loaded["raw_events"] == 10000
        assert result.total_records == 11020

        # Verify TRUNCATE was executed to ensure repeatable ingestion
        mock_cursor.execute.assert_called_once_with(
            "TRUNCATE TABLE raw_events, raw_customers, raw_campaigns CASCADE;"
        )

        # Verify bulk executemany was called three times (campaigns, customers, events)
        assert mock_cursor.executemany.call_count == 3

        # First call: campaigns (20 records)
        args_camp = mock_cursor.executemany.call_args_list[0]
        assert "INSERT INTO raw_campaigns" in args_camp[0][0]
        assert len(args_camp[0][1]) == 20

        # Second call: customers (1,000 records)
        args_cust = mock_cursor.executemany.call_args_list[1]
        assert "INSERT INTO raw_customers" in args_cust[0][0]
        assert len(args_cust[0][1]) == 1000

        # Third call: events (10,000 records)
        args_evt = mock_cursor.executemany.call_args_list[2]
        assert "INSERT INTO raw_events" in args_evt[0][0]
        assert len(args_evt[0][1]) == 10000

        # Verify transaction commit was called
        mock_conn.commit.assert_called_once()


def test_ingest_data_database_failure_handling(tmp_path: Path):
    """Verify that a database failure triggers rollback and raises DatabaseError."""
    generate_all_datasets(tmp_path, seed=42)

    mock_cursor = MagicMock()
    mock_cursor.executemany.side_effect = errors.ForeignKeyViolation("Key not present in table")
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.ingestion.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        with pytest.raises(DatabaseError, match="Database ingestion failed"):
            ingest_data(data_dir=tmp_path)

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
