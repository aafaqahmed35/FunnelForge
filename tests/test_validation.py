"""Unit tests for FunnelForge validation rules."""

from datetime import date
from unittest.mock import patch

import pytest

from funnelforge.validation import (
    IssueCategory,
    categorize_reason,
    is_blank,
    parse_date,
    parse_numeric,
    parse_timestamp,
    validate_campaign,
    validate_customer,
    validate_email_format,
    validate_event,
)


def test_is_blank():
    """Verify is_blank accurately detects empty, None, and whitespace values."""
    assert is_blank(None) is True
    assert is_blank("") is True
    assert is_blank("   ") is True
    assert is_blank(float("nan")) is True
    assert is_blank("valid") is False
    assert is_blank(123) is False
    assert is_blank(0) is False


def test_validate_email_format():
    """Verify email formatting validator accepts valid and catches invalid formats."""
    # Valid emails
    assert validate_email_format("user@example.com") is None
    assert validate_email_format("john.doe+tag@sub.domain.co") is None
    assert validate_email_format("test_123@mail.org") is None

    # Invalid emails
    assert "Invalid email format" in validate_email_format("not-an-email")
    assert "Invalid email format" in validate_email_format("user@@domain.com")
    assert "Invalid email format" in validate_email_format("missing_at.com")
    assert "Invalid email format" in validate_email_format("user@nodotdomain")
    assert "Invalid email format" in validate_email_format("spaces in email@domain.com")
    assert "Missing email" in validate_email_format("")


def test_parse_date_and_timestamp():
    """Verify date and timestamp parsers."""
    # Dates
    d, err = parse_date("2024-06-15", "start_date")
    assert err is None
    assert d == date(2024, 6, 15)

    _, err = parse_date("not-a-date", "start_date")
    assert "Invalid date format" in err

    _, err = parse_date("", "start_date")
    assert "Missing start_date" in err

    # Timestamps
    ts, err = parse_timestamp("2024-06-15T12:30:00+00:00", "event_timestamp")
    assert err is None
    assert ts.year == 2024 and ts.hour == 12

    _, err = parse_timestamp("invalid-ts", "event_timestamp")
    assert "Invalid timestamp format" in err


def test_validate_campaign_success():
    """Verify clean campaign passes validation."""
    valid_record = {
        "campaign_id": "CMP-001",
        "campaign_name": "Summer Launch",
        "channel": "Email",
        "budget": 15000.0,
        "start_date": "2024-06-01",
        "end_date": "2024-07-01",
    }
    errors = validate_campaign(valid_record, seen_ids=set())
    assert errors == []


def test_validate_campaign_errors_and_business_rules():
    """Verify campaign validation catches missing fields, duplicate IDs, and invalid dates."""
    # End date precedes start date
    bad_dates = {
        "campaign_id": "CMP-002",
        "campaign_name": "Autumn Sale",
        "channel": "Social Media",
        "budget": 5000.0,
        "start_date": "2024-09-15",
        "end_date": "2024-09-01",
    }
    errors = validate_campaign(bad_dates, seen_ids=set())
    assert any("precedes start_date" in e for e in errors)

    # Missing campaign_id and missing name
    missing_fields = {
        "campaign_id": None,
        "campaign_name": "",
        "channel": "Search",
        "budget": 1000.0,
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
    }
    errors = validate_campaign(missing_fields, seen_ids=set())
    assert "Missing campaign_id" in errors
    assert "Missing campaign_name" in errors

    # Duplicate campaign_id
    duplicate = {
        "campaign_id": "CMP-001",
        "campaign_name": "Duplicate Promo",
        "channel": "Display",
        "budget": 2000.0,
        "start_date": "2024-03-01",
        "end_date": "2024-04-01",
    }
    errors = validate_campaign(duplicate, seen_ids={"CMP-001"})
    assert any("Duplicate campaign_id" in e for e in errors)


def test_validate_customer_multiple_errors_on_one_record():
    """Verify customer validation captures multiple simultaneous errors on a single record."""
    multi_error_record = {
        "customer_id": "CUST-0001",
        "customer_name": "",                  # Error 1: Missing name
        "email": "invalid_email_format",      # Error 2: Invalid email format
        "acquisition_source": "Social Media",
        "signup_date": "2024-05-10",
    }
    errors = validate_customer(multi_error_record, seen_ids={"CUST-0001"})  # Error 3: Duplicate ID
    assert len(errors) == 3
    assert any("Duplicate customer_id" in e for e in errors)
    assert any("Missing customer_name" in e for e in errors)
    assert any("Invalid email format" in e for e in errors)


def test_validate_event_business_rules_and_referential_integrity():
    """Verify event validation enforces FK references and revenue business rules."""
    valid_customers = {"CUST-0001", "CUST-0002"}
    valid_campaigns = {"CMP-001"}

    # 1. Nonexistent customer and campaign references
    bad_fk_event = {
        "event_id": "EVT-00001",
        "customer_id": "CUST-9999",  # Does not exist
        "campaign_id": "CMP-999",    # Does not exist
        "event_type": "impression",
        "event_timestamp": "2024-06-01T10:00:00+00:00",
        "revenue": None,
    }
    errors = validate_event(
        bad_fk_event,
        seen_ids=set(),
        valid_customer_ids=valid_customers,
        valid_campaign_ids=valid_campaigns,
    )
    assert any("does not exist in accepted customers" in e for e in errors)
    assert any("does not exist in accepted campaigns" in e for e in errors)

    # 2. Negative revenue on conversion
    neg_rev_event = {
        "event_id": "EVT-00002",
        "customer_id": "CUST-0001",
        "campaign_id": "CMP-001",
        "event_type": "conversion",
        "event_timestamp": "2024-06-01T10:00:00+00:00",
        "revenue": -45.0,
    }
    errors = validate_event(
        neg_rev_event,
        seen_ids=set(),
        valid_customer_ids=valid_customers,
        valid_campaign_ids=valid_campaigns,
    )
    assert any("Negative revenue not allowed" in e for e in errors)

    # 3. Non-conversion carrying revenue
    click_with_rev = {
        "event_id": "EVT-00003",
        "customer_id": "CUST-0001",
        "campaign_id": "CMP-001",
        "event_type": "click",
        "event_timestamp": "2024-06-01T10:00:00+00:00",
        "revenue": 50.0,
    }
    errors = validate_event(
        click_with_rev,
        seen_ids=set(),
        valid_customer_ids=valid_customers,
        valid_campaign_ids=valid_campaigns,
    )
    assert any("Non-conversion event of type 'click' must not have revenue" in e for e in errors)

    # 4. Conversion missing revenue
    conv_missing_rev = {
        "event_id": "EVT-00004",
        "customer_id": "CUST-0001",
        "campaign_id": "CMP-001",
        "event_type": "conversion",
        "event_timestamp": "2024-06-01T10:00:00+00:00",
        "revenue": None,
    }
    errors = validate_event(
        conv_missing_rev,
        seen_ids=set(),
        valid_customer_ids=valid_customers,
        valid_campaign_ids=valid_campaigns,
    )
    assert any("Conversion event missing valid revenue" in e for e in errors)

    # 5. Invalid event type
    bad_type = {
        "event_id": "EVT-00005",
        "customer_id": "CUST-0001",
        "campaign_id": "CMP-001",
        "event_type": "hover",
        "event_timestamp": "2024-06-01T10:00:00+00:00",
        "revenue": None,
    }
    errors = validate_event(
        bad_type,
        seen_ids=set(),
        valid_customer_ids=valid_customers,
        valid_campaign_ids=valid_campaigns,
    )
    assert any("Invalid event_type: 'hover'" in e for e in errors)


def test_categorize_reason():
    """Verify categorization of rejection reasons."""
    assert categorize_reason("Missing customer_name") == IssueCategory.MISSING_REQUIRED
    assert categorize_reason("Duplicate customer_id: 'CUST-001'") == IssueCategory.DUPLICATE_RECORD
    assert categorize_reason("Invalid email format: 'xyz'") == IssueCategory.INVALID_FORMAT
    assert categorize_reason("Referenced customer_id does not exist") == IssueCategory.REFERENTIAL_INTEGRITY
    assert categorize_reason("Negative revenue not allowed") == IssueCategory.BUSINESS_RULE
    assert categorize_reason("Campaign end_date precedes start_date") == IssueCategory.BUSINESS_RULE
