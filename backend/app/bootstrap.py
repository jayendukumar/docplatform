"""Apply migrations and seed without logging credentials or database exceptions."""
import json
from pathlib import Path
import sys
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.config import load_settings
from app.database import create_database
from app.migrations import migrate
from app.models import Template
from app.storage import create_store

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "welcome.json"


def seed(engine, store):
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    key = "templates/sample-welcome/v1.json"
    with engine.begin() as connection:
        if connection.execute(select(Template.id).where(Template.id == "sample-welcome")).first():
            return
        # Store first: a failed database transaction can leave an unreferenced object,
        # but cannot publish metadata pointing to an object that was never written.
        store.put(key, json.dumps(sample, ensure_ascii=False).encode("utf-8"))
        connection.execute(insert(Template).values(
            id="sample-welcome", name=sample["name"], object_key=key, schema_version=1,
        ).on_conflict_do_nothing(index_elements=[Template.id]))


def main():
    engine = None
    try:
        settings = load_settings()
        engine = create_database(settings)
        migrate(engine)
        store = create_store(settings)
        store.check()
        if settings.seed_sample:
            seed(engine, store)
        print("Foundation initialized: migrations, storage and sample are ready")
        return 0
    except Exception:
        print("Foundation initialization failed; check database, storage and configuration", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
