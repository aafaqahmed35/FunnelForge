"""Synthetic marketing data generator for FunnelForge.

Produces realistic raw marketing data for:
- campaigns (20 records)
- customers (1,000 records)
- events (10,000 records)

Supports both clean generation (P1) and intentional dirty-data generation (P2)
with full reproducibility via configurable seeds.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Standard marketing channels
MARKETING_CHANNELS = ["Email", "Social Media", "Search", "Display", "Referral"]

# Customer acquisition sources
ACQUISITION_SOURCES = [
    "Organic Search",
    "Paid Search",
    "Social Media",
    "Email Campaign",
    "Referral",
    "Display Ads",
    "Direct",
]

# Campaign theme names
CAMPAIGN_THEMES = [
    ("Winter Kickoff", "Email"),
    ("Spring Brand Awareness", "Social Media"),
    ("Q1 Search Dominance", "Search"),
    ("Display Retargeting Alpha", "Display"),
    ("Partner Referral Sprint", "Referral"),
    ("Spring Flash Promo", "Email"),
    ("Social Story Ads", "Social Media"),
    ("High-Intent Search Blitz", "Search"),
    ("Display Programmatic Wave", "Display"),
    ("Customer Advocacy Referral", "Referral"),
    ("Summer Launchpad", "Email"),
    ("Mid-Year Video Ads", "Social Media"),
    ("Search Expansion Tier 1", "Search"),
    ("Banner Remarketing Beta", "Display"),
    ("Influencer Referral Push", "Referral"),
    ("Back to School Email Blast", "Email"),
    ("Autumn Lead Gen", "Social Media"),
    ("Q3 Search Maximizer", "Search"),
    ("Display Audience Network", "Display"),
    ("VIP Customer Referral Program", "Referral"),
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
]

DOMAINS = ["example.com", "mail.com", "inbox.org", "testcorp.io", "webmail.net"]


def generate_campaigns(
    count: int = 20,
    rng: Optional[random.Random] = None,
    dirty: bool = False,
) -> pd.DataFrame:
    """Generate synthetic marketing campaigns (clean or with intentional dirty records)."""
    r = rng or random.Random(42)
    campaigns: List[Dict] = []
    base_date = date(2024, 1, 1)

    for i in range(count):
        theme_idx = i % len(CAMPAIGN_THEMES)
        theme_name, default_channel = CAMPAIGN_THEMES[theme_idx]

        start_offset = (i * 16) + r.randint(0, 5)
        duration_days = r.randint(30, 90)
        c_start = base_date + timedelta(days=start_offset)
        c_end = c_start + timedelta(days=duration_days)

        budget = round(r.uniform(5000.0, 75000.0), 2)
        campaign_id = f"CMP-{i + 1:03d}"
        campaign_name = f"{theme_name} {2024}"

        campaigns.append({
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "channel": default_channel,
            "budget": budget,
            "start_date": c_start.isoformat(),
            "end_date": c_end.isoformat(),
        })

    if dirty:
        # Intentionally inject specific data quality issues into designated records
        # 1. Missing campaign name
        if count > 2:
            campaigns[2]["campaign_name"] = None

        # 2. Missing campaign identifier
        if count > 5:
            campaigns[5]["campaign_id"] = None

        # 3. Invalid date range (end_date precedes start_date)
        if count > 12:
            s_dt = date.fromisoformat(campaigns[12]["start_date"])
            campaigns[12]["end_date"] = (s_dt - timedelta(days=15)).isoformat()

    return pd.DataFrame(campaigns)


def generate_customers(
    count: int = 1000,
    rng: Optional[random.Random] = None,
    dirty: bool = False,
) -> pd.DataFrame:
    """Generate synthetic customer profiles (clean or with intentional dirty records)."""
    r = rng or random.Random(42)
    customers: List[Dict] = []
    base_date = date(2024, 1, 1)

    for i in range(count):
        cust_id = f"CUST-{i + 1:04d}"
        first = r.choice(FIRST_NAMES)
        last = r.choice(LAST_NAMES)
        domain = r.choice(DOMAINS)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}.{i + 1}@{domain}"
        source = r.choice(ACQUISITION_SOURCES)

        signup_offset = r.randint(0, 360)
        signup_dt = base_date + timedelta(days=signup_offset)

        customers.append({
            "customer_id": cust_id,
            "customer_name": name,
            "email": email,
            "acquisition_source": source,
            "signup_date": signup_dt.isoformat(),
        })

    if dirty and count >= 40:
        # Intentionally inject realistic dirty records
        # 1. Missing customer names (10 records: indices 10..19)
        for idx in range(10, 20):
            customers[idx]["customer_name"] = None

        # 2. Invalid email formats (10 records: indices 20..29)
        invalid_emails = [
            "invalid-email-address",
            "missing_at_sign.com",
            "double@@signs.org",
            "user@nodotdomain",
            "@missing_username.com",
            "spaces in email@domain.com",
            "user@.com",
            "user@domain..com",
            "just_letters",
            "user@",
        ]
        for i, idx in enumerate(range(20, 30)):
            customers[idx]["email"] = invalid_emails[i % len(invalid_emails)]

        # 3. Duplicate customer records (10 records: indices 30..39 duplicate earlier IDs)
        for i, idx in enumerate(range(30, 40)):
            customers[idx]["customer_id"] = f"CUST-{i + 1:04d}"

        # 4. Multi-error record: index 40 has both missing name and invalid email
        if count > 40:
            customers[40]["customer_name"] = None
            customers[40]["email"] = "corrupted-email"

    return pd.DataFrame(customers)


def generate_events(
    campaigns_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    count: int = 10000,
    rng: Optional[random.Random] = None,
    dirty: bool = False,
) -> pd.DataFrame:
    """Generate synthetic funnel events referencing campaigns and customers."""
    r = rng or random.Random(42)
    events: List[Dict] = []

    campaign_lookup: Dict[str, Tuple[datetime, datetime]] = {}
    for _, row in campaigns_df.iterrows():
        cid = str(row["campaign_id"])
        try:
            s_date = date.fromisoformat(str(row["start_date"]))
            e_date = date.fromisoformat(str(row["end_date"]))
            if e_date < s_date:
                e_date = s_date + timedelta(days=30)
        except Exception:
            s_date = date(2024, 1, 1)
            e_date = date(2024, 12, 31)

        s_dt = datetime(s_date.year, s_date.month, s_date.day, 0, 0, 0, tzinfo=timezone.utc)
        e_dt = datetime(e_date.year, e_date.month, e_date.day, 23, 59, 59, tzinfo=timezone.utc)
        campaign_lookup[cid] = (s_dt, e_dt)

    campaign_ids = [str(cid) for cid in campaigns_df["campaign_id"].dropna()]
    if not campaign_ids:
        campaign_ids = ["CMP-001"]
        campaign_lookup["CMP-001"] = (
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
        )

    customer_ids = [str(cid) for cid in customers_df["customer_id"].dropna()]
    if not customer_ids:
        customer_ids = ["CUST-0001"]

    event_types = ["impression", "click", "conversion"]
    weights = [0.70, 0.25, 0.05]

    for i in range(count):
        event_id = f"EVT-{i + 1:05d}"
        cust_id = r.choice(customer_ids)
        camp_id = r.choice(campaign_ids)
        ev_type = r.choices(event_types, weights=weights, k=1)[0]

        start_dt, end_dt = campaign_lookup.get(
            camp_id,
            (datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 12, 31, tzinfo=timezone.utc)),
        )
        window_seconds = int((end_dt - start_dt).total_seconds())
        offset_seconds = r.randint(0, max(1, window_seconds))
        ev_timestamp = start_dt + timedelta(seconds=offset_seconds)

        if ev_type == "conversion":
            revenue = round(r.uniform(15.0, 500.0), 2)
        else:
            revenue = None

        events.append({
            "event_id": event_id,
            "customer_id": cust_id,
            "campaign_id": camp_id,
            "event_type": ev_type,
            "event_timestamp": ev_timestamp.isoformat(),
            "revenue": revenue,
        })

    if dirty and count >= 500:
        # Intentionally inject realistic dirty events
        # 1. Nonexistent customer references (75 records: 50..124)
        for idx in range(50, 125):
            events[idx]["customer_id"] = "CUST-9999"

        # 2. Nonexistent campaign references (75 records: 125..199)
        for idx in range(125, 200):
            events[idx]["campaign_id"] = "CMP-999"

        # 3. Invalid event types (50 records: 200..249)
        bad_types = ["hover", "purchase", "bounce", "pageview", "cart_add"]
        for i, idx in enumerate(range(200, 250)):
            events[idx]["event_type"] = bad_types[i % len(bad_types)]

        # 4. Negative revenue on conversions (50 records: 250..299)
        for idx in range(250, 300):
            events[idx]["event_type"] = "conversion"
            events[idx]["revenue"] = -round(r.uniform(10.0, 150.0), 2)

        # 5. Non-conversion carrying conversion revenue (30 records: 300..329)
        for idx in range(300, 330):
            events[idx]["event_type"] = "click"
            events[idx]["revenue"] = 49.99

        # 6. Conversion missing revenue (30 records: 330..359)
        for idx in range(330, 360):
            events[idx]["event_type"] = "conversion"
            events[idx]["revenue"] = None

        # 7. Invalid timestamp format (50 records: 360..409)
        bad_timestamps = [
            "invalid-timestamp-format",
            "2024-13-45 25:99:99",
            "not-a-date",
            "2024/02/30",
            "9999-99-99T99:99:99Z",
        ]
        for i, idx in enumerate(range(360, 410)):
            events[idx]["event_timestamp"] = bad_timestamps[i % len(bad_timestamps)]

        # 8. Duplicate event IDs (20 records: 410..429 duplicate earlier IDs)
        for i, idx in enumerate(range(410, 430)):
            events[idx]["event_id"] = f"EVT-{i + 1:05d}"

        # 9. Multi-error record: index 430 has invalid event type AND negative revenue
        if count > 430:
            events[430]["event_type"] = "invalid_action"
            events[430]["revenue"] = -99.99

    return pd.DataFrame(events)


def generate_all_datasets(
    output_dir: Path,
    seed: int = 42,
    campaign_count: int = 20,
    customer_count: int = 1000,
    event_count: int = 10000,
    dirty: bool = False,
) -> Dict[str, Path]:
    """Generate all synthetic datasets, saving CSV files into output_dir.

    Returns dictionary mapping dataset names to saved file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    campaigns_df = generate_campaigns(count=campaign_count, rng=rng, dirty=dirty)
    customers_df = generate_customers(count=customer_count, rng=rng, dirty=dirty)
    events_df = generate_events(
        campaigns_df=campaigns_df,
        customers_df=customers_df,
        count=event_count,
        rng=rng,
        dirty=dirty,
    )

    campaigns_path = output_dir / "campaigns.csv"
    customers_path = output_dir / "customers.csv"
    events_path = output_dir / "events.csv"

    campaigns_df.to_csv(campaigns_path, index=False)
    customers_df.to_csv(customers_path, index=False)
    events_df.to_csv(events_path, index=False)

    return {
        "campaigns": campaigns_path,
        "customers": customers_path,
        "events": events_path,
    }
