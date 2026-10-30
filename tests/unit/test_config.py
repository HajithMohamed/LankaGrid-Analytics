"""
Unit tests for application configuration and environment variables.
"""
import pytest

from src.common.config import DatabaseConfig, get_config


@pytest.mark.unit
def test_database_config_defaults(monkeypatch):
    """Test default database configuration values when environment is minimal."""
    monkeypatch.setenv("POSTGRES_DB", "sl_grid_warehouse")
    monkeypatch.setenv("POSTGRES_USER", "grid_admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret123")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    db_cfg = DatabaseConfig.from_env()
    assert db_cfg.dbname == "sl_grid_warehouse"
    assert db_cfg.user == "grid_admin"
    assert db_cfg.password == "secret123"
    assert db_cfg.host == "localhost"
    assert db_cfg.port == 5432
    assert db_cfg.sslmode == "disable"


@pytest.mark.unit
def test_database_config_masks_password():
    """Ensure database password is masked in string representations for security."""
    db_cfg = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="sl_grid_warehouse",
        user="grid_admin",
        password="super_secret_password_do_not_leak",
    )
    repr_str = repr(db_cfg)
    assert "super_secret_password_do_not_leak" not in repr_str
    assert "******" in repr_str


@pytest.mark.unit
def test_app_config_paths():
    """Verify application directories are loaded properly."""
    cfg = get_config()
    assert cfg.raw_dir.name == "raw"
    assert cfg.staging_dir.name == "staging"
    assert cfg.processed_dir.name == "processed"
