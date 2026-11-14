"""Explicit validation rules for FunnelForge marketing data."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from funnelforge.generator import MARKETING_CHANNELS

# Standard RFC 5322 compliant simplified regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"
)

VALID_EVENT_TYPES = {"impression", "click", "conversion"}


class IssueCategory:
    """Standardized categories for data quality issues."""
    MISSING_REQUIRED = "Missing Required Fields"
    DUPLICATE_RECORD = "Duplicate Record"
    INVALID_FORMAT = "Invalid Format"
    BUSINESS_RULE = "Business Rule Violation"
    REFERENTIAL_INTEGRITY = "Referential Integrity"


def categorize_reason(reason: str) -> str:
    """Map a rejection reason message to its standard quality category."""
    lower = reason.lower()
    if "missing" in lower:
        return IssueCategory.MISSING_REQUIRED
    if "duplicate" in lower:
        return IssueCategory.DUPLICATE_RECORD
    if "referenc" in lower or "does not exist" in lower:
        return IssueCategory.REFERENTIAL_INTEGRITY
    if "invalid" in lower or "format" in lower:
        return IssueCategory.INVALID_FORMAT
    if "precedes" in lower or "revenue" in lower or "rule" in lower:
        return IssueCategory.BUSINESS_RULE
    return IssueCategory.BUSINESS_RULE


def is_blank(val: Any) -> bool:
    """Return True if value is None, NaN, or an empty/whitespace string."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    try:
        import pandas as pd
        if pd.isna(val):
            return True
    except ImportError:
        pass
    return False


def validate_email_format(email: Any) -> Optional[str]:
    """Validate email format. Returns error string if invalid."""
    if is_blank(email):
        return "Missing email"
    email_str = str(email).strip()
    if " " in email_str or not EMAIL_REGEX.match(email_str):
        return f"Invalid email format: '{email_str}'"
    return None


def parse_date(val: Any, field_name: str) -> Tuple[Optional[date], Optional[str]]:
    """Parse date in YYYY-MM-DD format."""
    if is_blank(val):
        return None, f"Missing {field_name}"
    try:
        parsed = date.fromisoformat(str(val).strip()[:10])
        return parsed, None
    except Exception:
        return None, f"Invalid date format for {field_name}: '{val}'"


def parse_timestamp(val: Any, field_name: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Parse ISO timestamp with timezone."""
    if is_blank(val):
        return None, f"Missing {field_name}"
    try:
        val_str = str(val).strip()
        # Handle ISO format
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        return dt, None
    except Exception:
        return None, f"Invalid timestamp format for {field_name}: '{val}'"


def parse_numeric(val: Any, field_name: str) -> Tuple[Optional[float], Optional[str]]:
    """Parse numeric float value."""
    if is_blank(val):
        return None, f"Missing {field_name}"
    try:
        f_val = float(val)
        return f_val, None
    except Exception:
        return None, f"Invalid numeric format for {field_name}: '{val}'"


def validate_campaign(
    record: Dict[str, Any],
    seen_ids: Set[str],
) -> List[str]:
    """Validate a single campaign record against format and business rules."""
    errors: List[str] = []

    # 1. Missing & Duplicate Campaign ID
    raw_id = record.get("campaign_id")
    if is_blank(raw_id):
        errors.append("Missing campaign_id")
    else:
        cid = str(raw_id).strip()
        if cid in seen_ids:
            errors.append(f"Duplicate campaign_id: '{cid}'")

    # 2. Campaign Name
    if is_blank(record.get("campaign_name")):
        errors.append("Missing campaign_name")

    # 3. Channel
    channel = record.get("channel")
    if is_blank(channel):
        errors.append("Missing channel")
    elif str(channel).strip() not in MARKETING_CHANNELS:
        errors.append(f"Invalid marketing channel: '{channel}'")

    # 4. Budget
    budget_val, budget_err = parse_numeric(record.get("budget"), "budget")
    if budget_err:
        errors.append(budget_err)
    elif budget_val is not None and budget_val < 0:
        errors.append(f"Budget cannot be negative: {budget_val}")

    # 5. Date validation & Business rule (end_date >= start_date)
    s_date, s_err = parse_date(record.get("start_date"), "start_date")
    if s_err:
        errors.append(s_err)

    e_date, e_err = parse_date(record.get("end_date"), "end_date")
    if e_err:
        errors.append(e_err)

    if s_date and e_date and e_date < s_date:
        errors.append(
            f"Campaign end_date ({e_date.isoformat()}) precedes start_date ({s_date.isoformat()})"
        )

    return errors


def validate_customer(
    record: Dict[str, Any],
    seen_ids: Set[str],
) -> List[str]:
    """Validate a single customer profile."""
    errors: List[str] = []

    # 1. Customer ID
    raw_id = record.get("customer_id")
    if is_blank(raw_id):
        errors.append("Missing customer_id")
    else:
        cid = str(raw_id).strip()
        if cid in seen_ids:
            errors.append(f"Duplicate customer_id: '{cid}'")

    # 2. Customer Name
    if is_blank(record.get("customer_name")):
        errors.append("Missing customer_name")

    # 3. Email
    email_err = validate_email_format(record.get("email"))
    if email_err:
        errors.append(email_err)

    # 4. Acquisition Source
    if is_blank(record.get("acquisition_source")):
        errors.append("Missing acquisition_source")

    # 5. Signup Date
    _, signup_err = parse_date(record.get("signup_date"), "signup_date")
    if signup_err:
        errors.append(signup_err)

    return errors


def validate_event(
    record: Dict[str, Any],
    seen_ids: Set[str],
    valid_customer_ids: Set[str],
    valid_campaign_ids: Set[str],
) -> List[str]:
    """Validate a single funnel event including referential integrity and revenue rules."""
    errors: List[str] = []

    # 1. Event ID
    raw_id = record.get("event_id")
    if is_blank(raw_id):
        errors.append("Missing event_id")
    else:
        eid = str(raw_id).strip()
        if eid in seen_ids:
            errors.append(f"Duplicate event_id: '{eid}'")

    # 2. Customer Reference & Referential Integrity
    raw_cust_id = record.get("customer_id")
    if is_blank(raw_cust_id):
        errors.append("Missing customer_id")
    else:
        cust_id = str(raw_cust_id).strip()
        if cust_id not in valid_customer_ids:
            errors.append(f"Referenced customer_id '{cust_id}' does not exist in accepted customers")

    # 3. Campaign Reference & Referential Integrity
    raw_camp_id = record.get("campaign_id")
    if is_blank(raw_camp_id):
        errors.append("Missing campaign_id")
    else:
        camp_id = str(raw_camp_id).strip()
        if camp_id not in valid_campaign_ids:
            errors.append(f"Referenced campaign_id '{camp_id}' does not exist in accepted campaigns")

    # 4. Event Type
    raw_type = record.get("event_type")
    ev_type = str(raw_type).strip() if not is_blank(raw_type) else ""
    if not ev_type:
        errors.append("Missing event_type")
    elif ev_type not in VALID_EVENT_TYPES:
        errors.append(f"Invalid event_type: '{ev_type}'")

    # 5. Event Timestamp
    _, ts_err = parse_timestamp(record.get("event_timestamp"), "event_timestamp")
    if ts_err:
        errors.append(ts_err)

    # 6. Revenue Business Rules
    raw_revenue = record.get("revenue")
    has_revenue = not is_blank(raw_revenue)

    if has_revenue:
        rev_num, rev_err = parse_numeric(raw_revenue, "revenue")
        if rev_err:
            errors.append(rev_err)
        else:
            assert rev_num is not None
            if rev_num < 0:
                errors.append(f"Negative revenue not allowed: {rev_num}")

            if ev_type and ev_type != "conversion":
                errors.append(
                    f"Non-conversion event of type '{ev_type}' must not have revenue (got {rev_num})"
                )
    else:
        if ev_type == "conversion":
            errors.append("Conversion event missing valid revenue")

    return errors

