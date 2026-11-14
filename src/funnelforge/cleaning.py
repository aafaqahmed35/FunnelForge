"""Data cleaning, deduplication, and quality assurance engine for FunnelForge.

Implements the complete P2 workflow:
1. Loads raw CSV data
2. Normalizes values
3. Validates records across missing values, duplicates, formats, business rules, and referential integrity
4. Separates accepted from rejected records while preserving lineage and multi-error reasons
5. Persists processed data and quality issues to disk and PostgreSQL
6. Compiles dynamic DataQualityReport
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from psycopg import Connection, errors
from psycopg.types.json import Jsonb

from funnelforge.config import DatabaseConfig, PROJECT_ROOT
from funnelforge.database import DatabaseError, get_connection
from funnelforge.ingestion import EXPECTED_COLUMNS, prepare_records, validate_csv
from funnelforge.quality import DatasetMetrics, QualityReport
from funnelforge.validation import (
    categorize_reason,
    is_blank,
    parse_date,
    parse_numeric,
    parse_timestamp,
    validate_campaign,
    validate_customer,
    validate_event,
)

logger = logging.getLogger(__name__)


def sanitize_for_json(val: Any) -> Any:
    """Recursively convert float('nan') and pd.NA to None for PostgreSQL JSONB compliance."""
    if isinstance(val, dict):
        return {k: sanitize_for_json(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [sanitize_for_json(v) for v in val]
    if isinstance(val, float) and pd.isna(val):
        return None
    return val


@dataclass
class RejectedRecord:
    """Represents a record that failed validation with full lineage audit data."""
    source_dataset: str
    record_id: Optional[str]
    rejection_reasons: List[str]
    original_record: Dict[str, Any]
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def rejection_reason(self) -> str:
        return "; ".join(self.rejection_reasons)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_dataset": self.source_dataset,
            "record_id": self.record_id or "UNKNOWN",
            "rejection_reason": self.rejection_reason,
            "rejection_count": len(self.rejection_reasons),
            "original_record": json.dumps(sanitize_for_json(self.original_record), default=str),
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class CleaningResult:
    """Container for the output of the data cleaning engine."""
    accepted_campaigns: pd.DataFrame
    accepted_customers: pd.DataFrame
    accepted_events: pd.DataFrame
    rejected_records: List[RejectedRecord]
    quality_report: QualityReport


def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize strings, trim whitespace, and convert blank strings to None."""
    cleaned: Dict[str, Any] = {}
    for k, v in raw.items():
        if is_blank(v):
            cleaned[k] = None
        elif isinstance(v, str):
            cleaned[k] = v.strip()
        else:
            cleaned[k] = v
    return cleaned


def clean_campaigns(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[RejectedRecord]]:
    """Clean and validate campaigns dataset."""
    accepted: List[Dict[str, Any]] = []
    rejected: List[RejectedRecord] = []
    seen_ids: Set[str] = set()

    for row in df.to_dict(orient="records"):
        norm = normalize_record(row)
        reasons = validate_campaign(norm, seen_ids)

        cid = norm.get("campaign_id")
        rec_id = str(cid) if cid else None

        if reasons:
            rejected.append(
                RejectedRecord(
                    source_dataset="campaigns",
                    record_id=rec_id,
                    rejection_reasons=reasons,
                    original_record=row,
                )
            )
        else:
            # Accepted: normalize types
            s_date, _ = parse_date(norm.get("start_date"), "start_date")
            e_date, _ = parse_date(norm.get("end_date"), "end_date")
            budget_val, _ = parse_numeric(norm.get("budget"), "budget")

            norm["start_date"] = s_date.isoformat() if s_date else norm.get("start_date")
            norm["end_date"] = e_date.isoformat() if e_date else norm.get("end_date")
            norm["budget"] = round(budget_val, 2) if budget_val is not None else 0.0

            accepted.append(norm)
            if rec_id:
                seen_ids.add(rec_id)

    accepted_df = pd.DataFrame(accepted, columns=EXPECTED_COLUMNS["campaigns"])
    return accepted_df, rejected


def clean_customers(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[RejectedRecord]]:
    """Clean and validate customers dataset."""
    accepted: List[Dict[str, Any]] = []
    rejected: List[RejectedRecord] = []
    seen_ids: Set[str] = set()

    for row in df.to_dict(orient="records"):
        norm = normalize_record(row)
        # Email normalization: lowercase
        if norm.get("email"):
            norm["email"] = str(norm["email"]).lower()

        reasons = validate_customer(norm, seen_ids)
        cid = norm.get("customer_id")
        rec_id = str(cid) if cid else None

        if reasons:
            rejected.append(
                RejectedRecord(
                    source_dataset="customers",
                    record_id=rec_id,
                    rejection_reasons=reasons,
                    original_record=row,
                )
            )
        else:
            s_date, _ = parse_date(norm.get("signup_date"), "signup_date")
            norm["signup_date"] = s_date.isoformat() if s_date else norm.get("signup_date")

            accepted.append(norm)
            if rec_id:
                seen_ids.add(rec_id)

    accepted_df = pd.DataFrame(accepted, columns=EXPECTED_COLUMNS["customers"])
    return accepted_df, rejected


def clean_events(
    df: pd.DataFrame,
    valid_customer_ids: Set[str],
    valid_campaign_ids: Set[str],
) -> Tuple[pd.DataFrame, List[RejectedRecord]]:
    """Clean and validate events dataset, enforcing referential integrity."""
    accepted: List[Dict[str, Any]] = []
    rejected: List[RejectedRecord] = []
    seen_ids: Set[str] = set()

    for row in df.to_dict(orient="records"):
        norm = normalize_record(row)
        if norm.get("event_type"):
            norm["event_type"] = str(norm["event_type"]).lower()

        reasons = validate_event(norm, seen_ids, valid_customer_ids, valid_campaign_ids)
        eid = norm.get("event_id")
        rec_id = str(eid) if eid else None

        if reasons:
            rejected.append(
                RejectedRecord(
                    source_dataset="events",
                    record_id=rec_id,
                    rejection_reasons=reasons,
                    original_record=row,
                )
            )
        else:
            ts, _ = parse_timestamp(norm.get("event_timestamp"), "event_timestamp")
            norm["event_timestamp"] = ts.isoformat() if ts else norm.get("event_timestamp")

            if norm.get("event_type") == "conversion" and norm.get("revenue") is not None:
                r_val, _ = parse_numeric(norm.get("revenue"), "revenue")
                norm["revenue"] = round(r_val, 2) if r_val is not None else None
            else:
                norm["revenue"] = None

            accepted.append(norm)
            if rec_id:
                seen_ids.add(rec_id)

    accepted_df = pd.DataFrame(accepted, columns=EXPECTED_COLUMNS["events"])
    return accepted_df, rejected


def build_quality_report(
    raw_counts: Dict[str, int],
    accepted_counts: Dict[str, int],
    rejected_records: List[RejectedRecord],
) -> QualityReport:
    """Aggregate quality metrics, issue categories, and dataset summaries."""
    dataset_metrics: Dict[str, DatasetMetrics] = {}
    for ds in ["campaigns", "customers", "events"]:
        examined = raw_counts.get(ds, 0)
        accepted = accepted_counts.get(ds, 0)
        rejected = examined - accepted
        dataset_metrics[ds] = DatasetMetrics(
            name=ds,
            examined=examined,
            accepted=accepted,
            rejected=rejected,
        )

    issues_by_category: Dict[str, int] = {}
    issues_by_dataset: Dict[str, int] = {}
    reasons_counter: Counter = Counter()

    for rej in rejected_records:
        issues_by_dataset[rej.source_dataset] = issues_by_dataset.get(rej.source_dataset, 0) + 1
        for reason in rej.rejection_reasons:
            reasons_counter[reason] += 1
            cat = categorize_reason(reason)
            issues_by_category[cat] = issues_by_category.get(cat, 0) + 1

    return QualityReport(
        datasets=dataset_metrics,
        issues_by_category=issues_by_category,
        issues_by_dataset=issues_by_dataset,
        rejection_reasons_counter=reasons_counter,
    )


def save_processed_and_rejected(
    cleaning_result: CleaningResult,
    processed_dir: Path,
    rejected_dir: Path,
) -> None:
    """Save accepted records to processed_dir and rejected records to rejected_dir."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    # Save processed CSVs
    cleaning_result.accepted_campaigns.to_csv(processed_dir / "campaigns.csv", index=False)
    cleaning_result.accepted_customers.to_csv(processed_dir / "customers.csv", index=False)
    cleaning_result.accepted_events.to_csv(processed_dir / "events.csv", index=False)

    # Save rejected records per dataset and combined audit file
    rejected_by_dataset: Dict[str, List[Dict[str, Any]]] = {
        "campaigns": [],
        "customers": [],
        "events": [],
    }

    all_rejected_dicts: List[Dict[str, Any]] = []
    for rej in cleaning_result.rejected_records:
        d = rej.to_dict()
        all_rejected_dicts.append(d)
        if rej.source_dataset in rejected_by_dataset:
            rejected_by_dataset[rej.source_dataset].append(d)

    # Combined audit CSV
    pd.DataFrame(all_rejected_dicts).to_csv(rejected_dir / "data_quality_issues.csv", index=False)

    # Per-dataset rejected files
    for ds, items in rejected_by_dataset.items():
        pd.DataFrame(items).to_csv(rejected_dir / f"{ds}_rejected.csv", index=False)


def persist_processed_data(
    cleaning_result: CleaningResult,
    config: Optional[DatabaseConfig] = None,
) -> None:
    """Persist accepted records and quality issues into PostgreSQL transactionally."""
    campaign_records = prepare_records(
        cleaning_result.accepted_campaigns, EXPECTED_COLUMNS["campaigns"]
    )
    customer_records = prepare_records(
        cleaning_result.accepted_customers, EXPECTED_COLUMNS["customers"]
    )
    event_records = prepare_records(
        cleaning_result.accepted_events, EXPECTED_COLUMNS["events"]
    )

    issue_records = [
        (
            rej.source_dataset,
            rej.record_id,
            rej.rejection_reason,
            Jsonb(sanitize_for_json(rej.original_record)),
            rej.detected_at,
        )
        for rej in cleaning_result.rejected_records
    ]

    sql_campaigns = """
        INSERT INTO processed_campaigns (campaign_id, campaign_name, channel, budget, start_date, end_date)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    sql_customers = """
        INSERT INTO processed_customers (customer_id, customer_name, email, acquisition_source, signup_date)
        VALUES (%s, %s, %s, %s, %s);
    """
    sql_events = """
        INSERT INTO processed_events (event_id, customer_id, campaign_id, event_type, event_timestamp, revenue)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    sql_issues = """
        INSERT INTO data_quality_issues (source_dataset, record_id, rejection_reason, original_record, detected_at)
        VALUES (%s, %s, %s, %s, %s);
    """

    with get_connection(config) as conn:
        with conn.cursor() as cur:
            try:
                # Transactional table replacement for processed tables and audit issues
                cur.execute(
                    "TRUNCATE TABLE processed_events, processed_customers, processed_campaigns CASCADE;"
                )
                cur.execute("TRUNCATE TABLE data_quality_issues;")

                # Bulk insert processed data
                cur.executemany(sql_campaigns, campaign_records)
                cur.executemany(sql_customers, customer_records)
                cur.executemany(sql_events, event_records)

                # Bulk insert data quality issues
                if issue_records:
                    cur.executemany(sql_issues, issue_records)

                conn.commit()
                logger.info(
                    "Successfully persisted processed data (%d campaigns, %d customers, %d events) "
                    "and %d quality issues to PostgreSQL.",
                    len(campaign_records),
                    len(customer_records),
                    len(event_records),
                    len(issue_records),
                )
            except errors.Error as err:
                conn.rollback()
                msg = f"Failed to persist processed data to PostgreSQL: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err
            except Exception as err:
                conn.rollback()
                msg = f"Unexpected error persisting processed data: {err}"
                logger.error(msg)
                raise DatabaseError(msg) from err


def run_cleaning_pipeline(
    raw_data_dir: Path,
    processed_dir: Path,
    rejected_dir: Path,
    persist_db: bool = True,
    config: Optional[DatabaseConfig] = None,
) -> CleaningResult:
    """Execute the complete data cleaning and quality assurance pipeline."""
    # 1. Load raw CSVs
    campaigns_raw = validate_csv(raw_data_dir / "campaigns.csv", "campaigns")
    customers_raw = validate_csv(raw_data_dir / "customers.csv", "customers")
    events_raw = validate_csv(raw_data_dir / "events.csv", "events")

    raw_counts = {
        "campaigns": len(campaigns_raw),
        "customers": len(customers_raw),
        "events": len(events_raw),
    }

    # 2. Clean Campaigns
    accepted_camp_df, rej_camp = clean_campaigns(campaigns_raw)
    valid_campaign_ids = set(accepted_camp_df["campaign_id"].dropna().astype(str))

    # 3. Clean Customers
    accepted_cust_df, rej_cust = clean_customers(customers_raw)
    valid_customer_ids = set(accepted_cust_df["customer_id"].dropna().astype(str))

    # 4. Clean Events (with referential integrity check against accepted parent IDs)
    accepted_evt_df, rej_evt = clean_events(
        events_raw,
        valid_customer_ids=valid_customer_ids,
        valid_campaign_ids=valid_campaign_ids,
    )

    all_rejected = rej_camp + rej_cust + rej_evt

    accepted_counts = {
        "campaigns": len(accepted_camp_df),
        "customers": len(accepted_cust_df),
        "events": len(accepted_evt_df),
    }

    # 5. Build Quality Report
    report = build_quality_report(raw_counts, accepted_counts, all_rejected)

    result = CleaningResult(
        accepted_campaigns=accepted_camp_df,
        accepted_customers=accepted_cust_df,
        accepted_events=accepted_evt_df,
        rejected_records=all_rejected,
        quality_report=report,
    )

    # 6. Save results to disk
    save_processed_and_rejected(result, processed_dir, rejected_dir)

    # 7. Persist to PostgreSQL if requested
    if persist_db:
        persist_processed_data(result, config=config)

    # 8. Print quality summary
    result.quality_report.print_report()

    return result
