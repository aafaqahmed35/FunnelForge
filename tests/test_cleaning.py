"""Unit tests for FunnelForge cleaning and separation engine."""

from pathlib import Path

import pandas as pd
import pytest

from funnelforge.cleaning import (
    CleaningResult,
    clean_campaigns,
    clean_customers,
    clean_events,
    normalize_record,
    run_cleaning_pipeline,
    save_processed_and_rejected,
)
from funnelforge.generator import generate_all_datasets


def test_normalize_record():
    """Verify normalize_record trims whitespace and converts blanks to None."""
    raw = {
        "id": "  CUST-001  ",
        "name": "   ",
        "email": "user@test.com",
        "value": None,
    }
    cleaned = normalize_record(raw)
    assert cleaned["id"] == "CUST-001"
    assert cleaned["name"] is None
    assert cleaned["email"] == "user@test.com"
    assert cleaned["value"] is None


def test_clean_campaigns_separation():
    """Verify campaigns are correctly partitioned into accepted and rejected."""
    df = pd.DataFrame([
        {
            "campaign_id": "CMP-001",
            "campaign_name": "Valid 1",
            "channel": "Email",
            "budget": 1000.0,
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
        },
        {
            "campaign_id": "CMP-002",
            "campaign_name": "",  # Missing name
            "channel": "Email",
            "budget": 1000.0,
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
        },
        {
            "campaign_id": "CMP-001",  # Duplicate ID
            "campaign_name": "Valid Duplicate",
            "channel": "Email",
            "budget": 1000.0,
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
        },
    ])
    accepted, rejected = clean_campaigns(df)
    assert len(accepted) == 1
    assert len(rejected) == 2
    assert accepted.iloc[0]["campaign_id"] == "CMP-001"
    assert rejected[0].record_id == "CMP-002"
    assert "Missing campaign_name" in rejected[0].rejection_reasons
    assert "Duplicate campaign_id: 'CMP-001'" in rejected[1].rejection_reasons


def test_clean_customers_deduplication():
    """Verify deduplication strategy retains first occurrence and rejects subsequent."""
    df = pd.DataFrame([
        {
            "customer_id": "CUST-001",
            "customer_name": "Alice First",
            "email": "alice@test.com",
            "acquisition_source": "Organic",
            "signup_date": "2024-01-01",
        },
        {
            "customer_id": "CUST-001",  # Duplicate
            "customer_name": "Alice Duplicate",
            "email": "alice.dup@test.com",
            "acquisition_source": "Paid",
            "signup_date": "2024-01-02",
        },
    ])
    accepted, rejected = clean_customers(df)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert accepted.iloc[0]["customer_name"] == "Alice First"
    assert "Duplicate customer_id: 'CUST-001'" in rejected[0].rejection_reasons


def test_clean_events_referential_integrity():
    """Verify events referencing rejected or nonexistent parents are rejected."""
    df = pd.DataFrame([
        {
            "event_id": "EVT-001",
            "customer_id": "CUST-001",  # Valid
            "campaign_id": "CMP-001",   # Valid
            "event_type": "impression",
            "event_timestamp": "2024-01-01T00:00:00+00:00",
            "revenue": None,
        },
        {
            "event_id": "EVT-002",
            "customer_id": "CUST-REJECTED",  # Invalid customer
            "campaign_id": "CMP-001",
            "event_type": "click",
            "event_timestamp": "2024-01-01T00:00:00+00:00",
            "revenue": None,
        },
    ])
    accepted, rejected = clean_events(
        df, valid_customer_ids={"CUST-001"}, valid_campaign_ids={"CMP-001"}
    )
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert accepted.iloc[0]["event_id"] == "EVT-001"
    assert any("does not exist in accepted customers" in r for r in rejected[0].rejection_reasons)


def test_save_processed_and_rejected_files(tmp_path: Path):
    """Verify save_processed_and_rejected writes all CSVs to disk."""
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    rej_dir = tmp_path / "rejected"

    generate_all_datasets(raw_dir, seed=42, dirty=True)

    result = run_cleaning_pipeline(
        raw_data_dir=raw_dir,
        processed_dir=proc_dir,
        rejected_dir=rej_dir,
        persist_db=False,
    )

    assert (proc_dir / "campaigns.csv").is_file()
    assert (proc_dir / "customers.csv").is_file()
    assert (proc_dir / "events.csv").is_file()

    assert (rej_dir / "data_quality_issues.csv").is_file()
    assert (rej_dir / "campaigns_rejected.csv").is_file()
    assert (rej_dir / "customers_rejected.csv").is_file()
    assert (rej_dir / "events_rejected.csv").is_file()

    issues_df = pd.read_csv(rej_dir / "data_quality_issues.csv")
    assert len(issues_df) == len(result.rejected_records)
    assert "rejection_reason" in issues_df.columns
    assert "original_record" in issues_df.columns

