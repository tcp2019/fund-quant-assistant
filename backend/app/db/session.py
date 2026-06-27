from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.db import models  # noqa: F401

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})

_FUND_METADATA_PURCHASE_COLUMNS = (
    ("purchase_status", "TEXT NOT NULL DEFAULT ''"),
    ("purchase_min_amount", "REAL"),
    ("daily_purchase_limit", "REAL"),
    ("themes_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("user_themes_json", "TEXT NOT NULL DEFAULT '[]'"),
)

_FUND_METRICS_CACHE_COLUMNS = (
    ("return_1y", "REAL"),
    ("peer_return_percentile_3m", "REAL"),
    ("computed_from", "TEXT NOT NULL DEFAULT ''"),
)

_STRATEGY_CONFIG_COLUMNS = (
    ("intra_category_mode", "TEXT NOT NULL DEFAULT 'equal'"),
    ("fund_target_weights_json", "TEXT NOT NULL DEFAULT '{}'"),
)

_SIGNAL_RECORD_COLUMNS = (
    ("interpretation", "TEXT"),
)


def _ensure_fund_metadata_purchase_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(fundmetadata)")).fetchall()
        }
        for name, ddl in _FUND_METADATA_PURCHASE_COLUMNS:
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE fundmetadata ADD COLUMN {name} {ddl}"))
        conn.commit()


def _ensure_fund_metrics_cache_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(fundmetricscache)")).fetchall()
        }
        for name, ddl in _FUND_METRICS_CACHE_COLUMNS:
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE fundmetricscache ADD COLUMN {name} {ddl}"))
        conn.commit()


def _ensure_strategy_config_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(strategyconfig)")).fetchall()
        }
        for name, ddl in _STRATEGY_CONFIG_COLUMNS:
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE strategyconfig ADD COLUMN {name} {ddl}"))
        conn.commit()


def _ensure_signal_record_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.connect() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(signalrecord)")).fetchall()
        }
        for name, ddl in _SIGNAL_RECORD_COLUMNS:
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE signalrecord ADD COLUMN {name} {ddl}"))
        conn.commit()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_fund_metadata_purchase_columns()
    _ensure_fund_metrics_cache_columns()
    _ensure_strategy_config_columns()
    _ensure_signal_record_columns()


def get_session():
    with Session(engine) as session:
        yield session
