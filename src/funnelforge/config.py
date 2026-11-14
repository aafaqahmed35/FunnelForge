"""Configuration management for FunnelForge."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Project root directory (funnelforge/../..)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class DatabaseConfig:
    """PostgreSQL database connection configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "funnelforge"
    user: str = "postgres"
    password: str = ""
    database_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create DatabaseConfig instance populated from environment variables."""
        db_url = os.getenv("DATABASE_URL")
        
        port_raw = os.getenv("DB_PORT", "5432")
        try:
            port = int(port_raw)
        except ValueError:
            raise ValueError(f"Invalid DB_PORT: {port_raw}. Must be an integer.")

        default_user = os.getenv("USER") or "postgres"
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=port,
            name=os.getenv("DB_NAME", "funnelforge"),
            user=os.getenv("DB_USER", default_user),
            password=os.getenv("DB_PASSWORD", ""),
            database_url=db_url,
        )

    def to_connection_params(self) -> Dict[str, Any]:
        """Return parameters dictionary for psycopg.connect()."""
        params: Dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
        }
        if self.password:
            params["password"] = self.password
        return params

    @property
    def connection_string(self) -> str:
        """Return PostgreSQL connection DSN string."""
        if self.database_url:
            return self.database_url
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class AppConfig:
    """FunnelForge application configuration."""

    db: DatabaseConfig = DatabaseConfig()
    data_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    rejected_dir: Path = PROJECT_ROOT / "data" / "rejected"
    reports_dir: Path = PROJECT_ROOT / "reports" / "generated"
    logs_dir: Path = PROJECT_ROOT / "logs"
    log_level: str = "INFO"
    random_seed: int = 42

    @classmethod
    def load(cls) -> AppConfig:
        """Load complete application configuration from environment."""
        db_cfg = DatabaseConfig.from_env()

        def resolve_dir(env_var: str, default: str) -> Path:
            raw_dir = os.getenv(env_var, default)
            p = Path(raw_dir)
            return p if p.is_absolute() else PROJECT_ROOT / p

        data_path = resolve_dir("DATA_DIR", "data/raw")
        proc_path = resolve_dir("PROCESSED_DATA_DIR", "data/processed")
        rej_path = resolve_dir("REJECTED_DATA_DIR", "data/rejected")
        rep_path = resolve_dir("REPORTS_DIR", "reports/generated")
        log_path = resolve_dir("LOGS_DIR", "logs")

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        seed_raw = os.getenv("RANDOM_SEED", "42")
        try:
            seed = int(seed_raw)
        except ValueError:
            seed = 42

        return cls(
            db=db_cfg,
            data_dir=data_path,
            processed_dir=proc_path,
            rejected_dir=rej_path,
            reports_dir=rep_path,
            logs_dir=log_path,
            log_level=log_level,
            random_seed=seed,
        )
