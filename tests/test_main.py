"""Unit tests for FunnelForge CLI main entry point."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from funnelforge.ingestion import IngestionResult
from funnelforge.main import main, run_pipeline


def test_main_cli_all_default():
    """Verify main() runs all stages by default."""
    with patch("funnelforge.main.run_pipeline") as mock_pipeline:
        ret = main([])
        assert ret == 0
        mock_pipeline.assert_called_once_with(
            data_dir=None,
            seed=None,
            do_generate=True,
            do_init_db=True,
            do_ingest=True,
        )


def test_main_cli_generate_only():
    """Verify main() with --generate runs only the generator."""
    with patch("funnelforge.main.run_pipeline") as mock_pipeline:
        ret = main(["--generate", "--seed", "123"])
        assert ret == 0
        mock_pipeline.assert_called_once_with(
            data_dir=None,
            seed=123,
            do_generate=True,
            do_init_db=False,
            do_ingest=False,
        )


def test_main_cli_init_db_only():
    """Verify main() with --init-db runs only schema initialization."""
    with patch("funnelforge.main.run_pipeline") as mock_pipeline:
        ret = main(["--init-db"])
        assert ret == 0
        mock_pipeline.assert_called_once_with(
            data_dir=None,
            seed=None,
            do_generate=False,
            do_init_db=True,
            do_ingest=False,
        )


def test_main_cli_ingest_only():
    """Verify main() with --ingest runs only ingestion."""
    with patch("funnelforge.main.run_pipeline") as mock_pipeline:
        ret = main(["--ingest"])
        assert ret == 0
        mock_pipeline.assert_called_once_with(
            data_dir=None,
            seed=None,
            do_generate=False,
            do_init_db=False,
            do_ingest=True,
        )


def test_run_pipeline_orchestration(tmp_path: Path):
    """Verify run_pipeline coordinates generator, schema init, and ingestion."""
    with patch("funnelforge.main.generate_all_datasets") as mock_gen, \
         patch("funnelforge.main.initialize_schema") as mock_init, \
         patch("funnelforge.main.ingest_data") as mock_ingest:

        mock_gen.return_value = {
            "campaigns": tmp_path / "campaigns.csv",
            "customers": tmp_path / "customers.csv",
            "events": tmp_path / "events.csv",
        }
        mock_ingest.return_value = IngestionResult(records_loaded={
            "raw_campaigns": 20, "raw_customers": 1000, "raw_events": 10000
        })

        run_pipeline(
            data_dir=tmp_path,
            seed=42,
            do_generate=True,
            do_init_db=True,
            do_ingest=True,
        )

        mock_gen.assert_called_once()
        mock_init.assert_called_once()
        mock_ingest.assert_called_once()
