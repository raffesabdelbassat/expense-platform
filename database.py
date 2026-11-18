import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expense_platform.db")
# Render and other hosts commonly provide the legacy postgres:// form.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_compatibility():
    """Add backwards-compatible columns that create_all does not migrate."""
    transaction_columns = {column["name"] for column in inspect(engine).get_columns("transactions")}
    if "currency" not in transaction_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE transactions ADD COLUMN currency VARCHAR(3)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
