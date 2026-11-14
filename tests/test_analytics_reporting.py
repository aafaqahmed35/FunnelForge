"""Unit tests for MarketingAnalytics terminal dashboard reporting."""

from unittest.mock import MagicMock

from funnelforge.analytics import MarketingAnalytics
from funnelforge.analytics_service import AnalyticsService


def test_marketing_analytics_report_all(capsys):
    """Verify report_all invokes all reporting sections and outputs formatted text."""
    mock_service = MagicMock(spec=AnalyticsService)
    mock_service.get_conversion_funnel.return_value = {
        "total_impressions": 5000,
        "total_clicks": 1500,
        "total_conversions": 300,
        "impression_to_click_pct": 30.0,
        "click_to_conversion_pct": 20.0,
        "overall_conversion_pct": 6.0,
    }
    mock_service.get_channel_performance.return_value = [
        {
            "channel": "Email",
            "total_campaigns": 3,
            "total_budget": 15000.0,
            "impressions": 5000,
            "clicks": 1500,
            "conversions": 300,
            "total_revenue": 10000.0,
            "roas": 0.67,
            "rank_revenue": 1,
        }
    ]
    mock_service.get_campaign_performance.return_value = [
        {
            "campaign_id": "CMP-001",
            "campaign_name": "Summer Promo",
            "channel": "Email",
            "budget": 5000.0,
            "conversions": 100,
            "total_revenue": 3000.0,
            "ctr_pct": 30.0,
            "roas": 0.6,
        }
    ]
    mock_service.get_revenue_analysis.return_value = [
        {
            "revenue_rank": 1,
            "campaign_name": "Summer Promo",
            "channel": "Email",
            "campaign_revenue": 3000.0,
            "revenue_contribution_pct": 100.0,
            "cumulative_revenue": 3000.0,
        }
    ]
    mock_service.get_monthly_revenue_trends.return_value = [
        {"month": "2024-01-01", "monthly_revenue": 3000.0, "conversions": 100, "avg_conversion_value": 30.0}
    ]
    mock_service.get_customer_analysis.return_value = [
        {
            "customer_id": "CUST-001",
            "customer_name": "Alice Smith",
            "acquisition_source": "Organic",
            "total_conversions": 2,
            "total_revenue": 300.0,
            "is_repeat_converter": True,
        }
    ]
    mock_service.get_acquisition_sources.return_value = [
        {
            "acquisition_source": "Organic",
            "total_customers": 10,
            "total_conversions": 5,
            "total_revenue": 1500.0,
            "revenue_per_customer": 150.0,
        }
    ]

    analytics = MarketingAnalytics(service=mock_service)
    analytics.report_all()

    captured = capsys.readouterr()
    assert "FUNNELFORGE MARKETING BUSINESS INTELLIGENCE DASHBOARD" in captured.out
    assert "CONVERSION FUNNEL" in captured.out
    assert "CHANNEL PERFORMANCE & EFFICIENCY" in captured.out
    assert "CAMPAIGN PERFORMANCE ANALYSIS" in captured.out
    assert "TOP 5 REVENUE GENERATING CAMPAIGNS" in captured.out
    assert "TOP CUSTOMERS BY REVENUE & VALUE" in captured.out
