from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_session():
    return SessionLocal()


def init_db():
    from db import models  # noqa – regisztrálja az összes modellt

    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()


def _migrate_add_missing_columns():
    """Meglévő adatbázishoz adja hozzá az új oszlopokat, ha még nem léteznek."""
    from sqlalchemy import text, inspect as sa_inspect

    inspector = sa_inspect(engine)

    if "offers" in inspector.get_table_names():
        offers_cols = [c["name"] for c in inspector.get_columns("offers")]
        if "projekt_neve" not in offers_cols:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE offers ADD COLUMN projekt_neve VARCHAR(300)")
                )
                conn.commit()
