"""Unit tests for FunnelForge data quality metrics and reporting."""

from collections import Counter

import pytest

from funnelforge.quality import DatasetMetrics, QualityReport


def test_dataset_metrics_calculations():
    """Verify acceptance and rejection rate percentage calculations."""
    m = DatasetMetrics(name="customers", examined=1000, accepted=970, rejected=30)
    assert m.examined == 1000
    assert m.accepted == 970
    assert m.rejected == 30
    assert pytest.approx(m.acceptance_rate, 0.01) == 97.0
    assert pytest.approx(m.rejection_rate, 0.01) == 3.0


def test_quality_report_overall_rates():
    """Verify aggregated acceptance and rejection calculations across multiple datasets."""
    datasets = {
        "campaigns": DatasetMetrics(name="campaigns", examined=20, accepted=18, rejected=2),
        "customers": DatasetMetrics(name="customers", examined=1000, accepted=970, rejected=30),
        "events": DatasetMetrics(name="events", examined=10000, accepted=9600, rejected=400),
    }

    report = QualityReport(
        datasets=datasets,
        issues_by_category={"Missing Required": 50, "Invalid Format": 120},
        issues_by_dataset={"campaigns": 2, "customers": 30, "events": 400},
        rejection_reasons_counter=Counter({"Invalid email": 30, "Missing name": 10}),
    )

    assert report.total_examined == 11020
    assert report.total_accepted == 10588
    assert report.total_rejected == 432

    expected_acc_rate = (10588 / 11020) * 100.0
    expected_rej_rate = (432 / 11020) * 100.0

    assert pytest.approx(report.overall_acceptance_rate, 0.01) == expected_acc_rate
    assert pytest.approx(report.overall_rejection_rate, 0.01) == expected_rej_rate


def test_quality_report_to_dict_and_print(capsys):
    """Verify report serialization and formatted console output."""
    datasets = {
        "campaigns": DatasetMetrics(name="campaigns", examined=20, accepted=18, rejected=2),
    }
    report = QualityReport(
        datasets=datasets,
        issues_by_category={"Invalid Format": 2},
        issues_by_dataset={"campaigns": 2},
        rejection_reasons_counter=Counter({"Missing campaign_id": 2}),
    )

    data = report.to_dict()
    assert data["total_examined"] == 20
    assert data["total_accepted"] == 18
    assert data["total_rejected"] == 2
    assert "campaigns" in data["datasets"]

    # Test print formatting
    report.print_report()
    captured = capsys.readouterr()
    assert "DATA QUALITY REPORT" in captured.out
    assert "Campaigns" in captured.out
    assert "Overall acceptance rate" in captured.out

