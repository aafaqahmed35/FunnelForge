"""Unit tests for reproducible dirty data generation."""

from pathlib import Path

import pandas as pd
import pytest

from funnelforge.generator import (
    generate_all_datasets,
    generate_campaigns,
    generate_customers,
    generate_events,
)


def test_clean_vs_dirty_generation():
    """Verify clean mode generates zero defects while dirty mode introduces intentional defects."""
    # Clean campaigns
    c_clean = generate_campaigns(count=20, dirty=False)
    assert c_clean["campaign_name"].notna().all()
    assert c_clean["campaign_id"].notna().all()
    assert (pd.to_datetime(c_clean["end_date"]) >= pd.to_datetime(c_clean["start_date"])).all()

    # Dirty campaigns
    c_dirty = generate_campaigns(count=20, dirty=True)
    assert c_dirty["campaign_name"].isna().any()  # Missing campaign name
    assert c_dirty["campaign_id"].isna().any()    # Missing campaign id
    assert (pd.to_datetime(c_dirty["end_date"]) < pd.to_datetime(c_dirty["start_date"])).any()


def test_dirty_customers_defects():
    """Verify dirty customers dataset contains all expected problem classes."""
    cust_dirty = generate_customers(count=1000, dirty=True)

    # 1. Missing names
    assert cust_dirty["customer_name"].isna().sum() >= 10

    # 2. Duplicate customer IDs
    assert cust_dirty["customer_id"].nunique() < 1000

    # 3. Invalid emails (using validate_email_format)
    from funnelforge.validation import validate_email_format
    invalid_email_count = sum(
        validate_email_format(email) is not None for email in cust_dirty["email"]
    )
    assert invalid_email_count >= 10


def test_dirty_events_defects():
    """Verify dirty events dataset contains all expected problem classes."""
    c_df = generate_campaigns(count=20, dirty=False)
    cust_df = generate_customers(count=1000, dirty=False)
    e_dirty = generate_events(c_df, cust_df, count=10000, dirty=True)

    # 1. Nonexistent customer and campaign references
    assert (e_dirty["customer_id"] == "CUST-9999").sum() >= 50
    assert (e_dirty["campaign_id"] == "CMP-999").sum() >= 50

    # 2. Invalid event types
    valid_types = {"impression", "click", "conversion"}
    invalid_types = set(e_dirty["event_type"].unique()) - valid_types
    assert len(invalid_types) > 0

    # 3. Negative revenue
    conversions = e_dirty[e_dirty["event_type"] == "conversion"]
    assert (conversions["revenue"] < 0).any()

    # 4. Non-conversions carrying revenue
    clicks = e_dirty[e_dirty["event_type"] == "click"]
    assert clicks["revenue"].notna().any()

    # 5. Invalid timestamps
    invalid_ts = e_dirty["event_timestamp"].str.contains("invalid|not-a-date|9999", na=False)
    assert invalid_ts.sum() >= 10


def test_dirty_generation_reproducibility(tmp_path: Path):
    """Verify that dirty data generation is completely reproducible with fixed seed."""
    dir_1 = tmp_path / "run1"
    dir_2 = tmp_path / "run2"

    generate_all_datasets(dir_1, seed=42, dirty=True)
    generate_all_datasets(dir_2, seed=42, dirty=True)

    for name in ["campaigns.csv", "customers.csv", "events.csv"]:
        df1 = pd.read_csv(dir_1 / name)
        df2 = pd.read_csv(dir_2 / name)
        pd.testing.assert_frame_equal(df1, df2)
