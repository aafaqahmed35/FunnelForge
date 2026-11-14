"""FunnelForge: Lightweight Marketing Data Analytics Pipeline."""

__version__ = "0.1.0"

from funnelforge.config import AppConfig, DatabaseConfig
from funnelforge.database import get_connection, initialize_schema
from funnelforge.generator import generate_all_datasets
from funnelforge.ingestion import IngestionResult, ingest_data

__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "get_connection",
    "initialize_schema",
    "generate_all_datasets",
    "IngestionResult",
    "ingest_data",
]
