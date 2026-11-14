"""Main CLI entry point for FunnelForge pipeline execution.

Supports running the complete pipeline (generation -> schema init -> ingestion)
or running individual steps independently.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from funnelforge.config import AppConfig
from funnelforge.database import initialize_schema
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import ingest_data


def run_pipeline(
    data_dir: Path,
    seed: int,
    do_generate: bool = True,
    do_init_db: bool = True,
    do_ingest: bool = True,
) -> None:
    """Execute selected steps or the end-to-end FunnelForge data pipeline."""
    config = AppConfig.load()
    target_data_dir = data_dir or config.data_dir
    target_seed = seed if seed is not None else config.random_seed

    if do_generate:
        print(f"\n[1/3] Generating synthetic datasets (seed={target_seed})...")
        paths = generate_all_datasets(output_dir=target_data_dir, seed=target_seed)
        print(f"  ✓ Generated campaigns: {paths['campaigns']} (20 records)")
        print(f"  ✓ Generated customers: {paths['customers']} (1,000 records)")
        print(f"  ✓ Generated events:    {paths['events']} (10,000 records)")
        print(f"  Total generated: 11,020 records across 3 files.")

    if do_init_db:
        print("\n[2/3] Initializing PostgreSQL schema...")
        initialize_schema(config=config.db)
        print("  ✓ Tables (raw_campaigns, raw_customers, raw_events) and indexes ready.")

    if do_ingest:
        print("\n[3/3] Ingesting CSV datasets into PostgreSQL...")
        result = ingest_data(data_dir=target_data_dir, config=config.db)
        print("Pipeline execution completed successfully!")


def main(argv: list[str] | None = None) -> int:
    """Parse command line arguments and execute requested pipeline tasks."""
    parser = argparse.ArgumentParser(
        prog="funnelforge",
        description="FunnelForge: Marketing Data Analytics Pipeline",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate synthetic CSV datasets only.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema only.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest existing CSV datasets into PostgreSQL only.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full pipeline: generate, initialize database, and ingest (default).",
    )
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
        help="Path to directory for CSV files (default: data/raw).",
    )

    args = parser.parse_args(argv)

    # Determine actions: if none specified or --all, run everything
    specific_action = args.generate or args.init_db or args.ingest
    run_all = args.all or not specific_action

    try:
        run_pipeline(
            data_dir=args.data_dir,
            seed=args.seed,
            do_generate=run_all or args.generate,
            do_init_db=run_all or args.init_db,
            do_ingest=run_all or args.ingest,
        )
        return 0
    except Exception as err:
        print(f"\n[ERROR] Pipeline failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
