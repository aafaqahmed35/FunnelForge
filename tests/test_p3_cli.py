"""Unit tests for P3 CLI analytics options."""

from unittest.mock import patch

from funnelforge.main import main, run_analytics_reporting


def test_main_cli_analytics_all():
    """Verify --analytics all invokes run_analytics_reporting."""
    with patch("funnelforge.main.run_analytics_reporting") as mock_run:
        ret = main(["--analytics", "all"])
        assert ret == 0
        mock_run.assert_called_once_with(topic="all", config=mock_run.call_args[1]["config"])


def test_main_cli_analytics_default_flag():
    """Verify bare --analytics defaults to 'all'."""
    with patch("funnelforge.main.run_analytics_reporting") as mock_run:
        ret = main(["--analytics"])
        assert ret == 0
        assert mock_run.call_args[1]["topic"] == "all"


def test_main_cli_analytics_topics():
    """Verify specific topics can be passed to --analytics."""
    for topic in ["campaigns", "channels", "funnel", "customers", "revenue"]:
        with patch("funnelforge.main.run_analytics_reporting") as mock_run:
            ret = main(["--analytics", topic])
            assert ret == 0
            assert mock_run.call_args[1]["topic"] == topic


def test_run_analytics_reporting_coordinator():
    """Verify run_analytics_reporting dispatches to appropriate MarketingAnalytics methods."""
    with patch("funnelforge.main.MarketingAnalytics") as mock_analytics_cls:
        instance = mock_analytics_cls.return_value

        run_analytics_reporting("campaigns")
        instance.report_campaign_performance.assert_called_once()

        run_analytics_reporting("channels")
        instance.report_channel_performance.assert_called_once()

        run_analytics_reporting("funnel")
        instance.report_conversion_funnel.assert_called_once()

        run_analytics_reporting("customers")
        instance.report_customer_analysis.assert_called_once()

        run_analytics_reporting("revenue")
        instance.report_revenue_analysis.assert_called_once()

        run_analytics_reporting("all")
        instance.report_all.assert_called_once()
