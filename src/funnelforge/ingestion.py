"""Data ingestion module for FunnelForge.

Reads raw CSV files, validates schemas, and performs transactional bulk
loading into PostgreSQL using parameterized SQL and table replacement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from psycopg import Connection, errors

from funnelforge.config import DatabaseConfig
from funnelforge.database import DatabaseError, get_connection

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS: Dict[str, List[str]] = {
    "campaigns": ["campaign_id", "campaign_name", "channel", "budget", "start_date", "end_date"],
    "customers": ["customer_id", "customer_name", "email", "acquisition_source", "signup_date"],
    "events": ["event_id", "customer_id", "campaign_id", "event_type", "event_timestamp", "revenue"],
}

TABLE_MAP: Dict[str, str] = {
    "campaigns": "raw_campaigns",
    "customers": "raw_customers",
    "events": "raw_events",
}


@dataclass
class IngestionResult:
    """Summary of records loaded into database tables."""

    records_loaded: Dict[str, int]

    @property
    def total_records(self) -> int:
        return sum(self.records_loaded.values())

    def print_summary(self) -> None:
        print("\n=== FunnelForge Ingestion Summary ===")
        for table, count in self.records_loaded.items():
            print(f"  • {table:<15}: {count:>6,d} records loaded")
        print(f"  -------------------------------------")
        print(f"  Total Ingested : {self.total_records:>6,d} records")
        print("=====================================\n")


def validate_csv(file_path: Path, dataset_key: str) -> pd.DataFrame:
    """Validate that a CSV file exists and contains all expected columns."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Required CSV file missing: {file_path}")

    expected = EXPECTED_COLUMNS[dataset_key]
    df = pd.read_csv(file_path)

    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(
            f"Validation failed for {file_path.name}: missing expected columns {missing}."
        )

    return df[expected]


def prepare_records(df: pd.DataFrame, expected_columns: List[str]) -> List[tuple]:
    """Convert a DataFrame into a list of tuples with NaNs sanitized to None for SQL NULL."""
    records: List[tuple] = []
    for row in df[expected_columns].itertuples(index=False, name=None):
        cleaned_row = tuple(None if pd.isna(val) else val for val in row)
        records.append(cleaned_row)
    return records


def ingest_data(
    data_dir: Path,
    config: Optional[DatabaseConfig] = None,
) -> IngestionResult:
    """Read CSV files, validate them, and perform transactional bulk ingestion into PostgreSQL.

    Uses transactional table replacement (TRUNCATE ... CASCADE) to ensure
    idempotent runs without duplicate records.
    """
    campaigns_file = data_dir / "campaigns.csv"
    customers_file = data_dir / "customers.csv"
    events_file = data_dir / "events.csv"

    # Step 1 & 2: Read and validate CSVs
    campaigns_df = validate_csv(campaigns_file, "campaigns")
    customers_df = validate_csv(customers_file, "customers")
    events_df = validate_csv(events_file, "events")

    campaign_records = prepare_records(campaigns_df, EXPECTED_COLUMNS["campaigns"])
    customer_records = prepare_records(customers_df, EXPECTED_COLUMNS["customers"])
    event_records = prepare_records(events_df, EXPECTED_COLUMNS["events"])

    sql_insert_campaigns = """
        INSERT INTO raw_campaigns (campaign_id, campaign_name, channel, budget, start_date, end_date)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    sql_insert_customers = """
        INSERT INTO raw_customers (customer_id, customer_name, email, acquisition_source, signup_date)
        VALUES (%s, %s, %s, %s, %s);
    """
    sql_insert_events = """
        INSERT INTO raw_events (event_id, customer_id, campaign_id, event_type, event_timestamp, revenue)
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    records_loaded: Dict[str, int] = {}

    with get_connection(config) as conn:
        with conn.cursor() as cur:
            try:
                # Step 7 & 8: Transactional table replacement ensures repeatability without duplicates
                cur.execute("TRUNCATE TABLE raw_events, raw_customers, raw_campaigns CASCADE;")

                # Bulk insert campaigns (satisfying FKs first)
                cur.executemany(sql_insert_campaigns, campaign_records)
                records_loaded["raw_campaigns"] = len(campaign_records)

                # Bulk insert customers
                cur.executemany(sql_insert_customers, customer_records)
                records_loaded["raw_customers"] = len(customer_records)

                # Bulk insert events
                cur.executemany(sql_insert_events, event_records)
                records_loaded["raw_events"] = len(event_records)

                conn.commit()
            except errors.Error as err:
                conn.rollback()
                msg = f"Database ingestion failed: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err
            except Exception as err:
                conn.rollback()
                msg = f"Unexpected error during ingestion: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err

    result = IngestionResult(records_loaded=records_loaded)
    result.print_summary()
    return result
