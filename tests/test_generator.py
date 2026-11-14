"""Unit tests for synthetic data generator."""

import random
from pathlib import Path

import pandas as pd
import pytest

from funnelforge.generator import (
    MARKETING_CHANNELS,
    generate_all_datasets,
    generate_campaigns,
    generate_customers,
    generate_events,
)
from funnelforge.ingestion import EXPECTED_COLUMNS


def test_campaigns_generation_counts_and_columns():
    """Verify that campaigns generator produces exactly 20 records with expected schema."""
    df = generate_campaigns(count=20, rng=random.Random(42))
    assert len(df) == 20
    assert list(df.columns) == EXPECTED_COLUMNS["campaigns"]
    assert df["campaign_id"].nunique() == 20
    assert df["channel"].isin(MARKETING_CHANNELS).all()
    assert (df["budget"] >= 0).all()
    assert (pd.to_datetime(df["end_date"]) >= pd.to_datetime(df["start_date"])).all()


def test_customers_generation_counts_and_columns():
    """Verify that customers generator produces exactly 1,000 records with unique IDs."""
    df = generate_customers(count=1000, rng=random.Random(42))
    assert len(df) == 1000
    assert list(df.columns) == EXPECTED_COLUMNS["customers"]
    assert df["customer_id"].nunique() == 1000
    assert df["email"].nunique() == 1000
    assert df["customer_name"].notna().all()
    assert df["acquisition_source"].notna().all()


def test_events_generation_counts_and_integrity():
    """Verify that events generator produces 10,000 records referencing valid FKs."""
    rng = random.Random(42)
    campaigns_df = generate_campaigns(count=20, rng=rng)
    customers_df = generate_customers(count=1000, rng=rng)
    events_df = generate_events(campaigns_df, customers_df, count=10000, rng=rng)

    assert len(events_df) == 10000
    assert list(events_df.columns) == EXPECTED_COLUMNS["events"]
    assert events_df["event_id"].nunique() == 10000

    # Foreign key references
    assert events_df["campaign_id"].isin(campaigns_df["campaign_id"]).all()
    assert events_df["customer_id"].isin(customers_df["customer_id"]).all()

    # Allowed event types
    valid_types = {"impression", "click", "conversion"}
    assert set(events_df["event_type"].unique()).issubset(valid_types)

    # Conversion revenue constraints: positive for conversions, None for non-conversions
    conversions = events_df[events_df["event_type"] == "conversion"]
    non_conversions = events_df[events_df["event_type"] != "conversion"]

    assert len(conversions) > 0
    assert (conversions["revenue"] > 0).all()
    assert non_conversions["revenue"].isna().all()


def test_reproducibility_with_fixed_seed(tmp_path: Path):
    """Verify that using the same seed produces identical datasets, and different seeds differ."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_c = tmp_path / "c"

    generate_all_datasets(dir_a, seed=42)
    generate_all_datasets(dir_b, seed=42)
    generate_all_datasets(dir_c, seed=99)

    for name in ["campaigns.csv", "customers.csv", "events.csv"]:
        df_a = pd.read_csv(dir_a / name)
        df_b = pd.read_csv(dir_b / name)
        df_c = pd.read_csv(dir_c / name)

        pd.testing.assert_frame_equal(df_a, df_b)
        assert not df_a.equals(df_c)


def test_generate_all_datasets_disk_output(tmp_path: Path):
    """Verify generate_all_datasets creates files with correct total counts (11,020)."""
    paths = generate_all_datasets(tmp_path, seed=42)

    assert paths["campaigns"].is_file()
    assert paths["customers"].is_file()
    assert paths["events"].is_file()

    c_count = len(pd.read_csv(paths["campaigns"]))
    u_count = len(pd.read_csv(paths["customers"]))
    e_count = len(pd.read_csv(paths["events"]))

    assert c_count == 20
    assert u_count == 1000
    assert e_count == 10000
    assert c_count + u_count + e_count == 11020
