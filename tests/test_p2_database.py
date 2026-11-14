"""Unit tests for P2 database operations and persistence using mocks."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from psycopg import errors

from funnelforge.cleaning import (
    CleaningResult,
    RejectedRecord,
    persist_processed_data,
)
from funnelforge.database import DatabaseError, initialize_p2_schema
from funnelforge.quality import QualityReport


def test_initialize_p2_schema_success(tmp_path: Path):
    """Verify initialize_p2_schema reads p2_schema.sql and executes DDL."""
    schema_file = tmp_path / "test_p2_schema.sql"
    sql_text = "CREATE TABLE test_proc (id INT PRIMARY KEY);"
    schema_file.write_text(sql_text, encoding="utf-8")

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.database.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        initialize_p2_schema(schema_path=schema_file)

        mock_cursor.execute.assert_called_once_with(sql_text)
        mock_conn.commit.assert_called_once()


def test_persist_processed_data_success():
    """Verify persist_processed_data performs transactional replacement and bulk insertion."""
    camp_df = pd.DataFrame([
        {
            "campaign_id": "CMP-001",
            "campaign_name": "Test",
            "channel": "Email",
            "budget": 1000.0,
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
        }
    ])
    cust_df = pd.DataFrame([
        {
            "customer_id": "CUST-001",
            "customer_name": "Alice",
            "email": "alice@test.com",
            "acquisition_source": "Organic",
            "signup_date": "2024-01-01",
        }
    ])
    evt_df = pd.DataFrame([
        {
            "event_id": "EVT-001",
            "customer_id": "CUST-001",
            "campaign_id": "CMP-001",
            "event_type": "impression",
            "event_timestamp": "2024-01-01T00:00:00+00:00",
            "revenue": None,
        }
    ])
    rejected = [
        RejectedRecord(
            source_dataset="customers",
            record_id="CUST-002",
            rejection_reasons=["Missing customer_name"],
            original_record={"customer_id": "CUST-002", "customer_name": None},
        )
    ]

    cleaning_res = CleaningResult(
        accepted_campaigns=camp_df,
        accepted_customers=cust_df,
        accepted_events=evt_df,
        rejected_records=rejected,
        quality_report=QualityReport(datasets={}),
    )

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.cleaning.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        persist_processed_data(cleaning_res)

        # 1. Truncation executed for idempotent table replacement
        mock_cursor.execute.assert_any_call(
            "TRUNCATE TABLE processed_events, processed_customers, processed_campaigns CASCADE;"
        )
        mock_cursor.execute.assert_any_call("TRUNCATE TABLE data_quality_issues;")

        # 2. Executemany called for each table: campaigns, customers, events, data_quality_issues
        assert mock_cursor.executemany.call_count == 4

        # 3. Transaction committed
        mock_conn.commit.assert_called_once()


def test_persist_processed_data_failure_rollback():
    """Verify persist_processed_data rolls back on database error."""
    cleaning_res = CleaningResult(
        accepted_campaigns=pd.DataFrame([{"campaign_id": "C1", "campaign_name": "T", "channel": "Email", "budget": 100, "start_date": "2024-01-01", "end_date": "2024-02-01"}]),
        accepted_customers=pd.DataFrame([{"customer_id": "U1", "customer_name": "A", "email": "a@b.com", "acquisition_source": "O", "signup_date": "2024-01-01"}]),
        accepted_events=pd.DataFrame([{"event_id": "E1", "customer_id": "U1", "campaign_id": "C1", "event_type": "click", "event_timestamp": "2024-01-01T00:00:00Z", "revenue": None}]),
        rejected_records=[],
        quality_report=QualityReport(datasets={}),
    )

    mock_cursor = MagicMock()
    mock_cursor.executemany.side_effect = errors.NotNullViolation("Column cannot be null")
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("funnelforge.cleaning.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        with pytest.raises(DatabaseError, match="Failed to persist processed data"):
            persist_processed_data(cleaning_res)

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

