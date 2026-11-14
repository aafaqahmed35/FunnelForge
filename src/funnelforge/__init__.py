"""FunnelForge: Lightweight Marketing Data Analytics Pipeline."""

__version__ = "0.3.0"

from funnelforge.analytics import MarketingAnalytics
from funnelforge.analytics_repository import AnalyticsRepository
from funnelforge.analytics_service import AnalyticsService
from funnelforge.cleaning import (
    CleaningResult,
    RejectedRecord,
    persist_processed_data,
    run_cleaning_pipeline,
)
from funnelforge.config import AppConfig, DatabaseConfig
from funnelforge.database import get_connection, initialize_p2_schema, initialize_schema
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import IngestionResult, ingest_data
from funnelforge.quality import DatasetMetrics, QualityReport

__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "get_connection",
    "initialize_schema",
    "initialize_p2_schema",
    "generate_all_datasets",
    "IngestionResult",
    "ingest_data",
    "CleaningResult",
    "RejectedRecord",
    "run_cleaning_pipeline",
    "persist_processed_data",
    "DatasetMetrics",
    "QualityReport",
    "MarketingAnalytics",
    "AnalyticsRepository",
    "AnalyticsService",
]
