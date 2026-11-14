"""Unit tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from funnelforge.config import AppConfig, DatabaseConfig


def test_database_config_defaults():
    """Verify default database settings when no environment variables are set."""
    with patch.dict(os.environ, {}, clear=True):
        cfg = DatabaseConfig.from_env()
        assert cfg.host == "localhost"
        assert cfg.port == 5432
        assert cfg.name == "funnelforge"
        assert cfg.user == "postgres"
        assert cfg.password == ""
        assert cfg.database_url is None

        params = cfg.to_connection_params()
        assert params == {
            "host": "localhost",
            "port": 5432,
            "dbname": "funnelforge",
            "user": "postgres",
        }
        assert "password" not in params
        assert cfg.connection_string == "postgresql://postgres@localhost:5432/funnelforge"


def test_database_config_from_custom_env():
    """Verify parsing of custom environment variables."""
    env = {
        "DB_HOST": "db.internal.corp",
        "DB_PORT": "5433",
        "DB_NAME": "marketing_prod",
        "DB_USER": "forge_user",
        "DB_PASSWORD": "secretpassword",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = DatabaseConfig.from_env()
        assert cfg.host == "db.internal.corp"
        assert cfg.port == 5433
        assert cfg.name == "marketing_prod"
        assert cfg.user == "forge_user"
        assert cfg.password == "secretpassword"

        params = cfg.to_connection_params()
        assert params["password"] == "secretpassword"
        assert cfg.connection_string == "postgresql://forge_user:secretpassword@db.internal.corp:5433/marketing_prod"


def test_database_config_invalid_port():
    """Verify that a non-integer port raises ValueError."""
    with patch.dict(os.environ, {"DB_PORT": "not-a-number"}, clear=True):
        with pytest.raises(ValueError, match="Invalid DB_PORT"):
            DatabaseConfig.from_env()


def test_database_config_with_url():
    """Verify connection string property when DATABASE_URL is explicitly set."""
    custom_url = "postgresql://myuser:mypass@db.host.com:5432/customdb"
    with patch.dict(os.environ, {"DATABASE_URL": custom_url}, clear=True):
        cfg = DatabaseConfig.from_env()
        assert cfg.database_url == custom_url
        assert cfg.connection_string == custom_url


def test_app_config_load():
    """Verify AppConfig correctly binds database, data path, and random seed."""
    env = {
        "DATA_DIR": "/tmp/custom_data",
        "RANDOM_SEED": "123",
    }
    with patch.dict(os.environ, env, clear=True):
        app_cfg = AppConfig.load()
        assert app_cfg.data_dir == Path("/tmp/custom_data")
        assert app_cfg.random_seed == 123
        assert isinstance(app_cfg.db, DatabaseConfig)
