"""Unit tests for the FunnelForge automated reporting engine."""

from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest

from funnelforge.config import DatabaseConfig
from funnelforge.quality import DatasetMetrics, QualityReport
from funnelforge.reporting import ReportGenerator, json_serializer


def test_json_serializer():
    now = datetime(2026, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
    today = date(2026, 11, 14)
    dec = Decimal("123.45")
    p = Path("/tmp/file.txt")

    assert json_serializer(now) == "2026-11-14T12:00:00+00:00"
    assert json_serializer(today) == "2026-11-14"
    assert json_serializer(dec) == 123.45
    assert json_serializer(p) == "/tmp/file.txt"

    class CustomObj:
        pass

    with pytest.raises(TypeError, match="not serializable to JSON"):
        json_serializer(CustomObj())


def test_report_generator_with_quality_report():
    qr = QualityReport(
        datasets={
            "campaigns": DatasetMetrics(name="campaigns", examined=20, accepted=18, rejected=2),
            "customers": DatasetMetrics(name="customers", examined=1000, accepted=980, rejected=20),
            "events": DatasetMetrics(name="events", examined=10000, accepted=9000, rejected=1000),
        },
        issues_by_category={"Invalid Format": 1022},
        issues_by_dataset={"campaigns": 2, "customers": 20, "events": 1000},
        rejection_reasons_counter=Counter({"Invalid email": 20}),
    )

    mock_service = MagicMock()
    mock_service.get_campaign_performance.return_value = [
        {"campaign_id": "CMP-001", "campaign_name": "Test", "channel": "Email", "budget": 1000.0, "total_revenue": 500.0}
    ]
    mock_service.get_conversion_funnel.return_value = {
        "total_impressions": 5000,
        "total_clicks": 2000,
        "total_conversions": 400,
        "overall_conversion_pct": 8.0,
    }
    mock_service.get_channel_performance.return_value = [
        {"channel": "Email", "total_revenue": 500.0, "roas": 0.5}
    ]
    mock_service.get_revenue_analysis.return_value = [
        {"campaign_name": "Test", "campaign_revenue": 500.0}
    ]

    reporter = ReportGenerator(service=mock_service, quality_report=qr)
    metrics = reporter.get_data_quality_metrics()

    assert metrics["total_examined"] == 11020
    assert metrics["total_accepted"] == 9998
    assert metrics["total_rejected"] == 1022
    assert "Invalid Format" in metrics["issues_by_category"]

    summary_text = reporter.generate_executive_summary_text()
    assert "FUNNELFORGE EXECUTIVE MARKETING SUMMARY" in summary_text
    assert "Total Marketing Campaigns :        1" in summary_text
    assert "Total Validated Customers :      980" in summary_text
    assert "Total Validated Events    :    7,400" in summary_text
    assert "Total Conversion Revenue  : $     500.00" in summary_text
    assert "Highest Revenue Channel   : Email ($500.00)" in summary_text


def test_report_generator_get_metrics_from_db():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # Mock sequence of fetchone and fetchall for DB query path
    mock_cur.fetchone.side_effect = [
        {"total_issues": 50},  # data_quality_issues count
        {"c": 20},            # processed_campaigns
        {"c": 980},           # processed_customers
        {"c": 9500},          # processed_events
    ]
    mock_cur.fetchall.return_value = [
        {"source_dataset": "events", "issue_count": 50}
    ]

    with patch("funnelforge.reporting.get_connection", return_value=mock_conn):
        reporter = ReportGenerator(quality_report=None)
        metrics = reporter.get_data_quality_metrics()

        assert metrics["total_examined"] == 10550
        assert metrics["total_accepted"] == 10500
        assert metrics["total_rejected"] == 50
        assert metrics["issues_by_dataset"]["events"] == 50


def test_report_generator_export_all(tmp_path: Path):
    mock_service = MagicMock()
    import pandas as pd
    df_empty = pd.DataFrame([{"col1": 1, "col2": 2}])
    mock_service.get_campaign_performance.side_effect = lambda as_df=False: df_empty if as_df else [{"col1": 1}]
    mock_service.get_channel_performance.side_effect = lambda as_df=False: df_empty if as_df else [{"col1": 1}]
    mock_service.get_customer_analysis.side_effect = lambda as_df=False, limit=None: df_empty if as_df else [{"col1": 1}]
    mock_service.get_revenue_analysis.side_effect = lambda as_df=False, top_n=None: df_empty if as_df else [{"col1": 1}]
    mock_service.get_acquisition_sources.return_value = []
    mock_service.get_monthly_revenue_trends.return_value = []
    mock_service.get_conversion_funnel.return_value = {"overall_conversion_pct": 5.0}

    qr = QualityReport(datasets={})
    reporter = ReportGenerator(service=mock_service, quality_report=qr)

    exported = reporter.export_all(output_dir=tmp_path)

    expected_keys = [
        "campaign_performance_csv",
        "channel_performance_csv",
        "customer_analysis_csv",
        "revenue_analysis_csv",
        "funnel_report_json",
        "executive_summary_txt",
    ]
    for key in expected_keys:
        assert key in exported
        assert exported[key].is_file()

    # Verify JSON content structure
    json_data = json.loads(exported["funnel_report_json"].read_text(encoding="utf-8"))
    assert json_data["metadata"]["system"] == "FunnelForge"
    assert "data_quality_report" in json_data
    assert "marketing_performance_report" in json_data


def test_report_generator_empty_dataset_handling(tmp_path: Path):
    mock_service = MagicMock()
    import pandas as pd
    mock_service.get_campaign_performance.return_value = []
    mock_service.get_channel_performance.return_value = []
    mock_service.get_customer_analysis.return_value = []
    mock_service.get_revenue_analysis.return_value = []
    mock_service.get_conversion_funnel.return_value = {}

    mock_conn = MagicMock()
    mock_conn.__enter__.side_effect = Exception("DB unavailable")

    with patch("funnelforge.reporting.get_connection", return_value=mock_conn):
        reporter = ReportGenerator(service=mock_service, quality_report=None)
        summary = reporter.generate_executive_summary_text()

        assert "Total Marketing Campaigns :        0" in summary
        assert "Total Conversion Revenue  : $       0.00" in summary
        assert "Highest Revenue Channel   : N/A" in summary
