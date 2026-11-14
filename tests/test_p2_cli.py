"""Unit tests for P2 CLI options and pipeline execution."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from funnelforge.cleaning import CleaningResult
from funnelforge.main import main, run_p2_quality_pipeline
from funnelforge.quality import QualityReport


def test_main_cli_p2_flag():
    """Verify --p2 flag invokes run_p2_quality_pipeline."""
    with patch("funnelforge.main.run_p2_quality_pipeline") as mock_p2:
        ret = main(["--p2", "--dirty", "--seed", "123"])
        assert ret == 0
        mock_p2.assert_called_once_with(
            raw_data_dir=None,
            processed_dir=None,
            rejected_dir=None,
            seed=123,
            dirty=True,
            persist_db=True,
            generate_first=True,
        )


def test_main_cli_clean_flag():
    """Verify --clean flag runs cleaning pipeline directly."""
    with patch("funnelforge.main.run_cleaning_pipeline") as mock_clean:
        ret = main(["--clean", "--no-db"])
        assert ret == 0
        mock_clean.assert_called_once()
        assert mock_clean.call_args[1]["persist_db"] is False


def test_main_cli_init_p2_db_flag():
    """Verify --init-p2-db initializes P2 schema."""
    with patch("funnelforge.main.initialize_p2_schema") as mock_init:
        ret = main(["--init-p2-db"])
        assert ret == 0
        mock_init.assert_called_once()


def test_run_p2_quality_pipeline_flow(tmp_path: Path):
    """Verify run_p2_quality_pipeline coordinates schema init, data cleaning, and persistence."""
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    rej_dir = tmp_path / "rejected"

    with patch("funnelforge.main.initialize_p2_schema") as mock_init, \
         patch("funnelforge.main.run_cleaning_pipeline") as mock_clean:

        mock_clean.return_value = MagicMock(spec=CleaningResult)

        run_p2_quality_pipeline(
            raw_data_dir=raw_dir,
            processed_dir=proc_dir,
            rejected_dir=rej_dir,
            seed=42,
            dirty=True,
            persist_db=True,
            generate_first=True,
        )

        mock_init.assert_called_once()
        mock_clean.assert_called_once_with(
            raw_data_dir=raw_dir,
            processed_dir=proc_dir,
            rejected_dir=rej_dir,
            persist_db=True,
            config=mock_init.call_args[1]["config"],
        )

