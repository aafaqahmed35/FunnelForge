"""Main CLI entry point for FunnelForge pipeline execution.

Supports running:
- Complete end-to-end automated pipeline (--pipeline [--dirty])
- P1: Data Foundation & Ingestion (generate -> schema init -> raw ingestion)
- P2: Data Cleaning & Quality Assurance (validate -> clean -> separate -> persist processed & issues -> quality report)
- P3: Marketing Analytics & Business Intelligence (--analytics [all|campaigns|channels|funnel|customers|revenue])
- P4: Automated Report Generation & Exports (--report)
- Individual modular operations independently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from funnelforge.analytics import MarketingAnalytics
from funnelforge.cleaning import run_cleaning_pipeline
from funnelforge.config import AppConfig
from funnelforge.database import initialize_p2_schema, initialize_schema
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import ingest_data
from funnelforge.logging import get_logger, setup_logging
from funnelforge.pipeline import execute_full_pipeline
from funnelforge.reporting import ReportGenerator

logger = get_logger("main")


def run_pipeline(
    data_dir: Path,
    seed: int,
    do_generate: bool = True,
    do_init_db: bool = True,
    do_ingest: bool = True,
    dirty: bool = False,
) -> None:
    """Execute selected steps or the end-to-end P1 raw data pipeline."""
    config = AppConfig.load()
    target_data_dir = data_dir or config.data_dir
    target_seed = seed if seed is not None else config.random_seed

    if do_generate:
        mode_str = "dirty data mode" if dirty else "clean data mode"
        print(f"\n[1/3] Generating synthetic datasets ({mode_str}, seed={target_seed})...")
        paths = generate_all_datasets(output_dir=target_data_dir, seed=target_seed, dirty=dirty)
        print(f"  ✓ Generated campaigns: {paths['campaigns']} (20 records)")
        print(f"  ✓ Generated customers: {paths['customers']} (1,000 records)")
        print(f"  ✓ Generated events:    {paths['events']} (10,000 records)")
        print(f"  Total generated: 11,020 records across 3 files.")

    if do_init_db:
        print("\n[2/3] Initializing PostgreSQL schema (raw tables)...")
        initialize_schema(config=config.db)
        print("  ✓ Tables (raw_campaigns, raw_customers, raw_events) and indexes ready.")

    if do_ingest:
        print("\n[3/3] Ingesting CSV datasets into PostgreSQL (raw tables)...")
        result = ingest_data(data_dir=target_data_dir, config=config.db)
        print("P1 pipeline execution completed successfully!")


# Alias for explicit naming
run_p1_pipeline = run_pipeline


def run_p2_quality_pipeline(
    raw_data_dir: Path,
    processed_dir: Path,
    rejected_dir: Path,
    seed: int,
    dirty: bool = False,
    persist_db: bool = True,
    generate_first: bool = False,
) -> None:
    """Execute the complete P2 Data Cleaning & Quality Assurance pipeline."""
    config = AppConfig.load()
    r_dir = raw_data_dir or config.data_dir
    p_dir = processed_dir or config.processed_dir
    j_dir = rejected_dir or config.rejected_dir
    target_seed = seed if seed is not None else config.random_seed

    raw_files_exist = (
        (r_dir / "campaigns.csv").is_file()
        and (r_dir / "customers.csv").is_file()
        and (r_dir / "events.csv").is_file()
    )

    if generate_first or not raw_files_exist or dirty:
        mode_str = "dirty data mode" if dirty else "clean data mode"
        print(f"\n[P2 Step 1/4] Generating synthetic datasets ({mode_str}, seed={target_seed})...")
        paths = generate_all_datasets(output_dir=r_dir, seed=target_seed, dirty=dirty)
        print(f"  ✓ Saved raw datasets in {r_dir}")

    if persist_db:
        print("\n[P2 Step 2/4] Initializing PostgreSQL schema (processed tables & quality audit)...")
        initialize_p2_schema(config=config.db)
        print("  ✓ Tables (processed_campaigns, processed_customers, processed_events, data_quality_issues) ready.")

    print("\n[P2 Step 3/4] Running Data Cleaning, Validation & Separation Engine...")
    result = run_cleaning_pipeline(
        raw_data_dir=r_dir,
        processed_dir=p_dir,
        rejected_dir=j_dir,
        persist_db=persist_db,
        config=config.db,
    )

    print(f"[P2 Step 4/4] Output files saved:")
    print(f"  ✓ Processed records : {p_dir}/")
    print(f"  ✓ Rejected records  : {j_dir}/")
    print("\nP2 Quality pipeline completed successfully!")


def run_analytics_reporting(
    topic: str = "all",
    config: Optional[AppConfig] = None,
) -> None:
    """Execute requested marketing analytics reporting queries."""
    cfg = config or AppConfig.load()
    analytics = MarketingAnalytics(config=cfg.db)

    topic_lower = topic.lower()
    if topic_lower == "campaigns":
        analytics.report_campaign_performance()
    elif topic_lower == "channels":
        analytics.report_channel_performance()
    elif topic_lower == "funnel":
        analytics.report_conversion_funnel()
    elif topic_lower == "customers":
        analytics.report_customer_analysis()
    elif topic_lower == "revenue":
        analytics.report_revenue_analysis()
    elif topic_lower == "all":
        analytics.report_all()
    else:
        raise ValueError(
            f"Unknown analytics topic '{topic}'. Choose from: all, campaigns, channels, funnel, customers, revenue"
        )


def main(argv: list[str] | None = None) -> int:
    """Parse command line arguments and execute requested pipeline tasks."""
    parser = argparse.ArgumentParser(
        prog="funnelforge",
        description="FunnelForge: Marketing Data Analytics Pipeline",
    )
    # Mode selection
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Run complete end-to-end automated pipeline (Extract -> Ingest -> Clean -> Analyze -> Report).",
    )
    parser.add_argument(
        "--report",
        "--reports",
        action="store_true",
        dest="report",
        help="Generate and export analytical reports (CSV, JSON, TXT).",
    )
    parser.add_argument(
        "--analytics",
        nargs="?",
        const="all",
        choices=["all", "campaigns", "channels", "funnel", "customers", "revenue"],
        help="Run SQL marketing analytics reporting (default: all).",
    )
    parser.add_argument(
        "--p2",
        action="store_true",
        help="Run complete P2 Data Cleaning & Quality Assurance pipeline.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full P1 pipeline: generate, initialize database, and ingest raw data (default).",
    )
    # Individual operations
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate synthetic CSV datasets only.",
    )
    parser.add_argument(
        "--dirty",
        action="store_true",
        help="Generate intentional dirty data for quality assurance testing.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize raw database schema only (P1).",
    )
    parser.add_argument(
        "--init-p2-db",
        action="store_true",
        help="Initialize processed and quality database schema only (P2).",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest existing CSV datasets into raw PostgreSQL tables only.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean, validate, and separate existing raw CSVs into processed and rejected.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip PostgreSQL persistence during cleaning workflow.",
    )
    # Parameter configuration
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible data generation (default: 42).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to raw CSV files directory (default: data/raw).",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Path to processed CSV files directory (default: data/processed).",
    )
    parser.add_argument(
        "--rejected-dir",
        type=Path,
        default=None,
        help="Path to rejected CSV files directory (default: data/rejected).",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Path to reports export directory (default: reports/generated).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO).",
    )

    args = parser.parse_args(argv)
    config = AppConfig.load()
    setup_logging(log_level=args.log_level or config.log_level)

    try:
        # P4 Unified Pipeline
        if args.pipeline:
            status = execute_full_pipeline(
                dirty=args.dirty,
                seed=args.seed,
                config=config,
            )
            return 0 if status.status == "SUCCESS" else 1

        # P4 Report Export
        if args.report:
            reporter = ReportGenerator(config=config.db)
            out_dir = args.reports_dir or config.reports_dir
            paths = reporter.export_all(output_dir=out_dir)
            print(f"\nSuccessfully generated {len(paths)} reports in {out_dir}:")
            for key, path in paths.items():
                print(f"  • {key:<26}: {path}")
            print()
            return 0

        # P3 Analytics
        if args.analytics:
            run_analytics_reporting(topic=args.analytics, config=config)
            return 0

        # P2 Quality Pipeline
        if args.p2:
            run_p2_quality_pipeline(
                raw_data_dir=args.data_dir,
                processed_dir=args.processed_dir,
                rejected_dir=args.rejected_dir,
                seed=args.seed,
                dirty=args.dirty,
                persist_db=not args.no_db,
                generate_first=args.generate or args.dirty,
            )
            return 0

        if args.clean:
            run_cleaning_pipeline(
                raw_data_dir=args.data_dir or config.data_dir,
                processed_dir=args.processed_dir or config.processed_dir,
                rejected_dir=args.rejected_dir or config.rejected_dir,
                persist_db=not args.no_db,
                config=config.db,
            )
            return 0

        if args.init_p2_db:
            print("Initializing P2 database schema (processed tables & quality audit)...")
            initialize_p2_schema(config=config.db)
            print("  ✓ Tables ready.")
            return 0

        # P1 workflow actions
        specific_p1_action = args.generate or args.init_db or args.ingest
        run_all = args.all or not specific_p1_action

        kwargs = {
            "data_dir": args.data_dir,
            "seed": args.seed,
            "do_generate": run_all or args.generate,
            "do_init_db": run_all or args.init_db,
            "do_ingest": run_all or args.ingest,
        }
        if args.dirty:
            kwargs["dirty"] = True

        run_pipeline(**kwargs)
        return 0

    except Exception as err:
        logger.error("Pipeline failed: %s", err)
        print(f"\n[ERROR] Pipeline failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
