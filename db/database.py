from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

import config
from db.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def _migrate_columns():
    """Fügt fehlende Spalten zu bestehenden Tabellen hinzu (einfache Auto-Migration)."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue  # Tabelle existiert noch nicht, wird von create_all erstellt

        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}

        for column in table.columns:
            if column.name not in existing_cols:
                col_type = column.type.compile(engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type}'
                    ))
                logger.info("Spalte '%s' zu Tabelle '%s' hinzugefügt.", column.name, table_name)


def init_db():
    """Erstellt alle Tabellen und migriert fehlende Spalten."""
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


@contextmanager
def get_session() -> Session:
    """Context-Manager für DB-Sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
