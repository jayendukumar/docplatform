from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]


def migration_config():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    return config


def expected_revision():
    return ScriptDirectory.from_config(migration_config()).get_current_head()


def migrate(engine):
    with engine.connect() as connection:
        # Session-level advisory lock serializes simultaneous bootstraps.
        connection.execute(text("SELECT pg_advisory_lock(6471120101)"))
        connection.commit()
        try:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(6471120101)"))
            connection.commit()
