"""Unit tests for AnalyticsService business logic and DataFrame formatting."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from funnelforge.analytics_repository import AnalyticsRepository
from funnelforge.analytics_service import AnalyticsService


@pytest.fixture
def mock_repo():
    return MagicMock(spec=AnalyticsRepository)


def test_service_campaign_performance_df(mock_repo):
    """Verify service converts campaign data into pandas DataFrame with expected columns."""
    mock_repo.get_campaign_performance.return_value = [
        {
            "campaign_id": "CMP-001",
            "campaign_name": "Summer Promo",
            "channel": "Email",
            "budget": 5000.0,
            "impressions": 1000,
            "clicks": 300,
            "conversions": 50,
            "total_revenue": 2500.0,
            "ctr_pct": 30.0,
            "conv_rate_pct": 16.67,
            "roas": 0.5,
        }
    ]

    service = AnalyticsService(repository=mock_repo)
    df = service.get_campaign_performance(as_df=True)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "ctr_pct" in df.columns
    assert "roas" in df.columns
    assert df.iloc[0]["campaign_id"] == "CMP-001"


def test_service_empty_campaign_performance_df(mock_repo):
    """Verify service handles empty campaign dataset without crashing."""
    mock_repo.get_campaign_performance.return_value = []

    service = AnalyticsService(repository=mock_repo)
    df = service.get_campaign_performance(as_df=True)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert "campaign_id" in df.columns
    assert "roas" in df.columns


def test_service_channel_performance(mock_repo):
    """Verify channel rankings and metrics extraction."""
    mock_repo.get_channel_performance.return_value = [
        {
            "channel": "Email",
            "total_campaigns": 3,
            "total_budget": 15000.0,
            "avg_budget": 5000.0,
            "impressions": 3000,
            "clicks": 900,
            "conversions": 150,
            "total_revenue": 7500.0,
            "ctr_pct": 30.0,
            "conv_rate_pct": 16.67,
            "roas": 0.5,
            "rank_revenue": 1,
            "rank_conversions": 1,
            "rank_efficiency": 1,
        }
    ]

    service = AnalyticsService(repository=mock_repo)
    data = service.get_channel_performance(as_df=False)
    assert len(data) == 1
    assert data[0]["rank_revenue"] == 1


def test_service_full_summary(mock_repo):
    """Verify service consolidates all analytics areas into summary dictionary."""
    mock_repo.get_conversion_funnel.return_value = {"total_impressions": 100}
    mock_repo.get_channel_performance.return_value = [{"channel": "Social"}]
    mock_repo.get_revenue_analysis.return_value = [{"campaign_id": "CMP-1"}]
    mock_repo.get_customer_analysis.return_value = [{"customer_id": "CUST-1"}]
    mock_repo.get_acquisition_source_performance.return_value = [{"acquisition_source": "Organic"}]
    mock_repo.get_monthly_revenue_trends.return_value = [{"month": "2024-01-01"}]

    service = AnalyticsService(repository=mock_repo)
    summary = service.get_full_summary()

    assert "funnel" in summary
    assert "channel_performance" in summary
    assert "top_campaigns" in summary
    assert "top_customers" in summary
    assert "acquisition_sources" in summary
    assert "monthly_trends" in summary
