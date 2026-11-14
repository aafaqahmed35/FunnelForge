"""Unit tests for the FunnelForge end-to-end pipeline orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from funnelforge.config import AppConfig
from funnelforge.ingestion import IngestionResult
from funnelforge.pipeline import PipelineOrchestrator, PipelineStatus, execute_full_pipeline
from funnelforge.quality import DatasetMetrics, QualityReport


def test_pipeline_status_print_summary(capsys):
    status = PipelineStatus(
        raw_records_processed=11020,
        accepted_records=9444,
        rejected_records=1576,
        data_acceptance_rate=85.7,
        total_campaigns=17,
        total_customers=969,
        total_events=8458,
        total_conversion_revenue=110889.16,
        overall_conversion_rate=7.27,
        reports_generated=6,
        status="SUCCESS",
    )
    status.print_summary()
    captured = capsys.readouterr().out

    assert "FUNNELFORGE PIPELINE" in captured
    assert "Raw Records Processed:         11,020" in captured
    assert "Accepted Records:               9,444" in captured
    assert "Rejected Records:               1,576" in captured
    assert "Data Acceptance Rate:           85.7%" in captured
    assert "Total Conversion Revenue:    $110,889.16" in captured
    assert "Pipeline Status: SUCCESS" in captured


@patch("funnelforge.pipeline.generate_all_datasets")
@patch("funnelforge.pipeline.initialize_schema")
@patch("funnelforge.pipeline.initialize_p2_schema")
@patch("funnelforge.pipeline.ingest_data")
@patch("funnelforge.pipeline.run_cleaning_pipeline")
@patch("funnelforge.pipeline.AnalyticsService")
@patch("funnelforge.pipeline.ReportGenerator")
def test_pipeline_orchestrator_clean_mode(
    mock_reporter_cls,
    mock_analytics_cls,
    mock_clean_pipeline,
    mock_ingest,
    mock_init_p2,
    mock_init_p1,
    mock_generate,
    tmp_path: Path,
):
    mock_generate.return_value = {
        "campaigns": tmp_path / "campaigns.csv",
        "customers": tmp_path / "customers.csv",
        "events": tmp_path / "events.csv",
    }
    mock_ingest.return_value = IngestionResult(
        records_loaded={"raw_campaigns": 20, "raw_customers": 1000, "raw_events": 10000}
    )

    qr = QualityReport(
        datasets={
            "campaigns": DatasetMetrics(name="campaigns", examined=20, accepted=20, rejected=0),
            "customers": DatasetMetrics(name="customers", examined=1000, accepted=1000, rejected=0),
            "events": DatasetMetrics(name="events", examined=10000, accepted=10000, rejected=0),
        }
    )
    mock_clean_res = MagicMock()
    mock_clean_res.quality_report = qr
    mock_clean_res.accepted_campaigns = [{}] * 20
    mock_clean_res.accepted_customers = [{}] * 1000
    mock_clean_res.accepted_events = [{}] * 10000
    mock_clean_res.rejected_records = []
    mock_clean_pipeline.return_value = mock_clean_res

    mock_service = MagicMock()
    mock_service.get_conversion_funnel.return_value = {"overall_conversion_pct": 7.1}
    mock_service.get_campaign_performance.return_value = [
        {"campaign_id": "CMP-001", "total_revenue": 100000.0}
    ]
    mock_analytics_cls.return_value = mock_service

    mock_reporter = MagicMock()
    mock_reporter.export_all.return_value = {"report1": tmp_path / "rep1.csv"}
    mock_reporter_cls.return_value = mock_reporter

    config = AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports")
    orchestrator = PipelineOrchestrator(config=config)

    status = orchestrator.run(dirty=False, export_reports=True)

    assert status.status == "SUCCESS"
    assert status.raw_records_processed == 11020
    assert status.accepted_records == 11020
    assert status.rejected_records == 0
    assert status.data_acceptance_rate == 100.0
    assert status.total_campaigns == 20
    assert status.total_customers == 1000
    assert status.total_events == 10000
    assert status.total_conversion_revenue == 100000.0
    assert status.overall_conversion_rate == 7.1
    assert status.reports_generated == 1

    mock_ingest.assert_called_once()
    mock_reporter.export_all.assert_called_once()


@patch("funnelforge.pipeline.generate_all_datasets")
@patch("funnelforge.pipeline.initialize_schema")
@patch("funnelforge.pipeline.initialize_p2_schema")
@patch("funnelforge.pipeline.ingest_data")
@patch("funnelforge.pipeline.run_cleaning_pipeline")
@patch("funnelforge.pipeline.AnalyticsService")
@patch("funnelforge.pipeline.ReportGenerator")
def test_pipeline_orchestrator_dirty_mode_skips_raw_ingest(
    mock_reporter_cls,
    mock_analytics_cls,
    mock_clean_pipeline,
    mock_ingest,
    mock_init_p2,
    mock_init_p1,
    mock_generate,
    tmp_path: Path,
):
    qr = QualityReport(
        datasets={
            "campaigns": DatasetMetrics(name="campaigns", examined=20, accepted=17, rejected=3),
            "customers": DatasetMetrics(name="customers", examined=1000, accepted=969, rejected=31),
            "events": DatasetMetrics(name="events", examined=10000, accepted=8458, rejected=1542),
        }
    )
    mock_clean_res = MagicMock()
    mock_clean_res.quality_report = qr
    mock_clean_res.accepted_campaigns = [{}] * 17
    mock_clean_res.accepted_customers = [{}] * 969
    mock_clean_res.accepted_events = [{}] * 8458
    mock_clean_res.rejected_records = [{}] * 1576
    mock_clean_pipeline.return_value = mock_clean_res

    mock_service = MagicMock()
    mock_service.get_conversion_funnel.return_value = {"overall_conversion_pct": 7.27}
    mock_service.get_campaign_performance.return_value = [
        {"campaign_id": "CMP-001", "total_revenue": 50000.0}
    ]
    mock_analytics_cls.return_value = mock_service

    config = AppConfig(data_dir=tmp_path / "data", reports_dir=tmp_path / "reports")
    orchestrator = PipelineOrchestrator(config=config)

    status = orchestrator.run(dirty=True, export_reports=False)

    assert status.status == "SUCCESS"
    assert status.raw_records_processed == 11020
    assert status.accepted_records == 9444
    assert status.rejected_records == 1576
    assert status.data_acceptance_rate == 85.7
    assert status.total_campaigns == 17
    assert status.total_customers == 969
    assert status.total_events == 8458

    # Raw ingest should NOT be called in dirty mode
    mock_ingest.assert_not_called()


@patch("funnelforge.pipeline.generate_all_datasets", side_effect=RuntimeError("Disk full"))
def test_pipeline_orchestrator_failure(mock_generate, tmp_path: Path):
    config = AppConfig(data_dir=tmp_path / "data")
    orchestrator = PipelineOrchestrator(config=config)

    with pytest.raises(RuntimeError, match="Disk full"):
        orchestrator.run(dirty=False)


@patch("funnelforge.pipeline.setup_logging")
@patch("funnelforge.pipeline.PipelineOrchestrator")
def test_execute_full_pipeline_helper(mock_orchestrator_cls, mock_setup_logging):
    mock_inst = MagicMock()
    mock_orchestrator_cls.return_value = mock_inst

    execute_full_pipeline(dirty=True, seed=99)

    mock_setup_logging.assert_called_once()
    mock_orchestrator_cls.assert_called_once()
    mock_inst.run.assert_called_once_with(dirty=True, seed=99)
