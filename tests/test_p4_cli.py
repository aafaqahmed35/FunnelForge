"""Unit tests for P4 CLI commands and flags."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from funnelforge.main import main
from funnelforge.pipeline import PipelineStatus


@patch("funnelforge.main.execute_full_pipeline")
def test_main_cli_pipeline_clean(mock_exec, monkeypatch):
    mock_status = PipelineStatus(status="SUCCESS")
    mock_exec.return_value = mock_status

    monkeypatch.setattr("sys.argv", ["funnelforge", "--pipeline"])
    main()

    assert mock_exec.call_count == 1
    call_args, call_kwargs = mock_exec.call_args
    assert call_kwargs["dirty"] is False
    assert call_kwargs["seed"] is None


@patch("funnelforge.main.execute_full_pipeline")
def test_main_cli_pipeline_dirty(mock_exec, monkeypatch):
    mock_status = PipelineStatus(status="SUCCESS")
    mock_exec.return_value = mock_status

    monkeypatch.setattr("sys.argv", ["funnelforge", "--pipeline", "--dirty", "--seed", "123"])
    main()

    assert mock_exec.call_count == 1
    call_args, call_kwargs = mock_exec.call_args
    assert call_kwargs["dirty"] is True
    assert call_kwargs["seed"] == 123


@patch("funnelforge.main.ReportGenerator")
def test_main_cli_report(mock_reporter_cls, monkeypatch, tmp_path: Path):
    mock_reporter = MagicMock()
    mock_reporter.export_all.return_value = {"report1": tmp_path / "rep1.csv"}
    mock_reporter_cls.return_value = mock_reporter

    monkeypatch.setattr("sys.argv", ["funnelforge", "--report", "--reports-dir", str(tmp_path)])
    main()

    mock_reporter.export_all.assert_called_once_with(output_dir=tmp_path)
