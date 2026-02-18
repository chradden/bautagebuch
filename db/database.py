from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

import config
from db.models import Base

engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Erstellt alle Tabellen."""
    Base.metadata.create_all(bind=engine)


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
