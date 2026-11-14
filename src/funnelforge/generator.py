"""Synthetic marketing data generator for FunnelForge.

Produces realistic, clean raw marketing data for:
- campaigns (20 records)
- customers (1,000 records)
- events (10,000 records)
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


def generate_campaigns(count: int = 20, rng: Optional[random.Random] = None) -> pd.DataFrame:
    """Generate synthetic marketing campaigns."""
    r = rng or random.Random(42)
    campaigns: List[Dict] = []
    base_date = date(2024, 1, 1)

    for i in range(count):
        theme_idx = i % len(CAMPAIGN_THEMES)
        theme_name, default_channel = CAMPAIGN_THEMES[theme_idx]
        
        # Space start dates across the year
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

    return pd.DataFrame(campaigns)


def generate_customers(count: int = 1000, rng: Optional[random.Random] = None) -> pd.DataFrame:
    """Generate synthetic customer profiles."""
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
        
        # Signup date distributed throughout the year
        signup_offset = r.randint(0, 360)
        signup_dt = base_date + timedelta(days=signup_offset)

        customers.append({
            "customer_id": cust_id,
            "customer_name": name,
            "email": email,
            "acquisition_source": source,
            "signup_date": signup_dt.isoformat(),
        })

    return pd.DataFrame(customers)


def generate_events(
    campaigns_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    count: int = 10000,
    rng: Optional[random.Random] = None,
) -> pd.DataFrame:
    """Generate synthetic funnel events referencing valid customers and campaigns."""
    r = rng or random.Random(42)
    events: List[Dict] = []

    # Map campaigns to datetime windows for realistic timestamps
    campaign_lookup: Dict[str, Tuple[datetime, datetime]] = {}
    for _, row in campaigns_df.iterrows():
        s_date = date.fromisoformat(str(row["start_date"]))
        e_date = date.fromisoformat(str(row["end_date"]))
        s_dt = datetime(s_date.year, s_date.month, s_date.day, 0, 0, 0, tzinfo=timezone.utc)
        e_dt = datetime(e_date.year, e_date.month, e_date.day, 23, 59, 59, tzinfo=timezone.utc)
        campaign_lookup[row["campaign_id"]] = (s_dt, e_dt)

    campaign_ids = list(campaigns_df["campaign_id"])
    customer_ids = list(customers_df["customer_id"])

    # Distribution: 70% impression, 25% click, 5% conversion
    event_types = ["impression", "click", "conversion"]
    weights = [0.70, 0.25, 0.05]

    for i in range(count):
        event_id = f"EVT-{i + 1:05d}"
        cust_id = r.choice(customer_ids)
        camp_id = r.choice(campaign_ids)
        ev_type = r.choices(event_types, weights=weights, k=1)[0]

        start_dt, end_dt = campaign_lookup[camp_id]
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

    return pd.DataFrame(events)


def generate_all_datasets(
    output_dir: Path,
    seed: int = 42,
    campaign_count: int = 20,
    customer_count: int = 1000,
    event_count: int = 10000,
) -> Dict[str, Path]:
    """Generate all synthetic datasets, saving CSV files into output_dir.

    Returns dictionary mapping dataset names to saved file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    campaigns_df = generate_campaigns(count=campaign_count, rng=rng)
    customers_df = generate_customers(count=customer_count, rng=rng)
    events_df = generate_events(
        campaigns_df=campaigns_df,
        customers_df=customers_df,
        count=event_count,
        rng=rng,
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
