"""End-to-end hardened pipeline orchestrator for FunnelForge."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from funnelforge.analytics_service import AnalyticsService
from funnelforge.cleaning import CleaningResult, run_cleaning_pipeline
from funnelforge.config import AppConfig, PROJECT_ROOT
from funnelforge.database import initialize_p2_schema, initialize_schema
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import ingest_data
from funnelforge.logging import get_logger, setup_logging
from funnelforge.reporting import ReportGenerator

logger = get_logger("pipeline")


@dataclass
class PipelineStatus:
    """Execution status and summary metrics for a pipeline run."""
    raw_records_processed: int = 0
    accepted_records: int = 0
    rejected_records: int = 0
    data_acceptance_rate: float = 0.0
    total_campaigns: int = 0
    total_customers: int = 0
    total_events: int = 0
    total_conversion_revenue: float = 0.0
    overall_conversion_rate: float = 0.0
    reports_generated: int = 0
    report_paths: Dict[str, Path] = field(default_factory=dict)
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    def print_summary(self) -> None:
        """Print the standardized execution summary banner."""
        print("\n" + "=" * 48)
        print("             FUNNELFORGE PIPELINE")
        print("=" * 48)
        print(f"Raw Records Processed:       {self.raw_records_processed:>8,d}")
        print(f"Accepted Records:            {self.accepted_records:>8,d}")
        print(f"Rejected Records:            {self.rejected_records:>8,d}")
        print(f"Data Acceptance Rate:        {self.data_acceptance_rate:>7.1f}%")
        print(f"Total Campaigns:             {self.total_campaigns:>8,d}")
        print(f"Total Customers:             {self.total_customers:>8,d}")
        print(f"Total Events:                {self.total_events:>8,d}")
        print(f"Total Conversion Revenue:    ${self.total_conversion_revenue:>10,.2f}")
        print(f"Overall Conversion Rate:     {self.overall_conversion_rate:>7.2f}%")
        print(f"Reports Generated:           {self.reports_generated:>8,d}")
        print(f"Pipeline Status: {self.status}")
        print("=" * 48 + "\n")


class PipelineOrchestrator:
    """Coordinates the full data engineering lifecycle:

    Extract -> Ingest -> Validate -> Clean -> Persist -> Analyze -> Report
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()

    def run(
        self,
        dirty: bool = False,
        seed: Optional[int] = None,
        export_reports: bool = True,
    ) -> PipelineStatus:
        """Execute the end-to-end automated marketing pipeline."""
        target_seed = seed if seed is not None else self.config.random_seed
        mode_label = "DIRTY-DATA" if dirty else "CLEAN-DATA"

        logger.info("==================================================")
        logger.info("FunnelForge Pipeline started in %s mode (seed=%d)", mode_label, target_seed)
        logger.info("==================================================")

        try:
            # 1. Source Data Generation
            logger.info("Step 1/6: Generating synthetic datasets...")
            raw_paths = generate_all_datasets(
                output_dir=self.config.data_dir,
                seed=target_seed,
                dirty=dirty,
            )
            logger.info(
                "Step 1/6: Datasets generated successfully in %s", self.config.data_dir
            )

            # 2. Database Schema Initialization (Raw & Processed)
            logger.info("Step 2/6: Initializing PostgreSQL database schemas...")
            initialize_schema(config=self.config.db)
            initialize_p2_schema(config=self.config.db)
            logger.info("Step 2/6: Schemas initialized and verified.")

            # 3. Raw Data Ingestion (P1 Layer)
            if not dirty:
                logger.info("Step 3/6: Ingesting raw datasets into raw PostgreSQL tables...")
                raw_ingest_result = ingest_data(
                    data_dir=self.config.data_dir,
                    config=self.config.db,
                )
                logger.info(
                    "Step 3/6: Raw ingestion completed (%d records).",
                    raw_ingest_result.total_records,
                )
            else:
                logger.info(
                    "Step 3/6: Dirty mode active — bypassing strict raw_* table landing "
                    "(P1 schema enforces NOT NULL/FK constraints). Raw CSV records will be "
                    "validated, cleaned, and partitioned into processed_* and data_quality_issues."
                )

            # 4. Data Cleaning, Validation & Separation (P2 Layer)
            logger.info("Step 4/6: Validating and cleaning datasets...")
            cleaning_result: CleaningResult = run_cleaning_pipeline(
                raw_data_dir=self.config.data_dir,
                processed_dir=self.config.processed_dir,
                rejected_dir=self.config.rejected_dir,
                persist_db=True,
                config=self.config.db,
            )
            logger.info(
                "Step 4/6: Validation completed. Accepted=%d, Rejected=%d",
                len(cleaning_result.accepted_campaigns)
                + len(cleaning_result.accepted_customers)
                + len(cleaning_result.accepted_events),
                len(cleaning_result.rejected_records),
            )

            # 5. Marketing Analytics Execution (P3 Layer)
            logger.info("Step 5/6: Executing analytical queries on processed data...")
            service = AnalyticsService(config=self.config.db)
            funnel_data = service.get_conversion_funnel()
            campaign_data = service.get_campaign_performance()
            logger.info("Step 5/6: Analytical queries completed.")

            # 6. Report Generation & Exports (P4 Layer)
            reports_map: Dict[str, Path] = {}
            if export_reports:
                logger.info("Step 6/6: Generating and exporting analytical reports...")
                reporter = ReportGenerator(
                    service=service,
                    config=self.config.db,
                    quality_report=cleaning_result.quality_report,
                )
                reports_map = reporter.export_all(output_dir=self.config.reports_dir)
                logger.info("Step 6/6: %d reports exported to %s", len(reports_map), self.config.reports_dir)

            # Calculate dynamic summary metrics
            raw_total = cleaning_result.quality_report.total_examined
            total_camps = len(cleaning_result.accepted_campaigns)
            total_custs = len(cleaning_result.accepted_customers)
            total_evts = len(cleaning_result.accepted_events)
            accepted_total = cleaning_result.quality_report.total_accepted
            rejected_total = cleaning_result.quality_report.total_rejected
            acc_rate = cleaning_result.quality_report.overall_acceptance_rate
            total_rev = sum(float(c.get("total_revenue", 0.0)) for c in campaign_data)
            ovr_conv_pct = float(funnel_data.get("overall_conversion_pct", 0.0) or 0.0)

            status = PipelineStatus(
                raw_records_processed=raw_total,
                accepted_records=accepted_total,
                rejected_records=rejected_total,
                data_acceptance_rate=round(acc_rate, 1),
                total_campaigns=total_camps,
                total_customers=total_custs,
                total_events=total_evts,
                total_conversion_revenue=round(total_rev, 2),
                overall_conversion_rate=round(ovr_conv_pct, 2),
                reports_generated=len(reports_map),
                report_paths=reports_map,
                status="SUCCESS",
            )

            status.print_summary()
            logger.info("Pipeline completed successfully.")
            return status

        except Exception as err:
            logger.error("Pipeline execution failed: %s", err, exc_info=True)
            failed_status = PipelineStatus(
                status="FAILED",
                error_message=str(err),
            )
            raise


def execute_full_pipeline(
    dirty: bool = False,
    seed: Optional[int] = None,
    config: Optional[AppConfig] = None,
) -> PipelineStatus:
    """Convenience helper to run the complete FunnelForge pipeline."""
    cfg = config or AppConfig.load()
    setup_logging(log_level=cfg.log_level, log_file=cfg.logs_dir / "funnelforge.log")
    orchestrator = PipelineOrchestrator(config=cfg)
    return orchestrator.run(dirty=dirty, seed=seed)
