from sqlalchemy import create_engine, text, URL
from sqlalchemy.engine import Engine
from app.config import Settings


def create_database(settings: Settings) -> Engine:
    url = URL.create("postgresql+pg8000", username=settings.db_user,
                     password=settings.db_password.get_secret_value(), host=settings.db_host,
                     port=settings.db_port, database=settings.db_name)
    return create_engine(url, pool_pre_ping=True, hide_parameters=True, pool_size=5,
                         max_overflow=5, pool_timeout=settings.db_connect_timeout_seconds,
                         connect_args={"timeout": settings.db_connect_timeout_seconds})


def check_database(engine: Engine, expected_revision: str):
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if revision != expected_revision:
            raise RuntimeError("Database migration required")
