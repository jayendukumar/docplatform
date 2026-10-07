"""Audit or remove templates whose latest definitions are byte-for-byte identical.

Dry-run is the default. ``--apply`` retains the oldest template in each exact
definition group, records aliases, removes duplicate versions, and removes their
stored objects. It never merges near-duplicates or versions from the canonical row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import load_settings  # noqa: E402
from app.database import create_database  # noqa: E402
from app.migrations import migrate  # noqa: E402
from app.models import Template, TemplateAlias, TemplateVersion  # noqa: E402
from app.storage import create_store  # noqa: E402


def groups(engine) -> list[tuple[str, list[dict]]]:
    with engine.connect() as connection:
        templates = connection.execute(select(Template.id, Template.name, Template.object_key, Template.created_at)).mappings().all()
        latest = {}
        for template in templates:
            version = connection.execute(select(TemplateVersion.definition_json).where(
                TemplateVersion.template_id == template["id"]).order_by(TemplateVersion.version.desc()).limit(1)).scalar_one_or_none()
            if version is None:
                continue
            digest = hashlib.sha256(version.encode("utf-8")).hexdigest()
            latest.setdefault(digest, []).append({**dict(template), "definition_json": version})
    return [(digest, sorted(items, key=lambda item: (item["created_at"], item["id"])))
            for digest, items in latest.items() if len(items) > 1]


def run(apply: bool) -> dict:
    settings = load_settings()
    engine = create_database(settings)
    migrate(engine)
    store = create_store(settings)
    duplicate_count = 0
    groups_seen = []
    duplicate_groups = groups(engine)
    with engine.begin() as connection:
        for digest, items in duplicate_groups:
            canonical = items[0]
            duplicates = items[1:]
            duplicate_count += len(duplicates)
            groups_seen.append({"definition_hash": digest, "canonical": canonical["id"],
                                "duplicates": [item["id"] for item in duplicates]})
            if not apply:
                continue
            for duplicate in duplicates:
                if connection.execute(select(TemplateAlias.duplicate_template_id).where(
                        TemplateAlias.duplicate_template_id == duplicate["id"])).scalar_one_or_none() is None:
                    connection.execute(TemplateAlias.__table__.insert().values(
                        duplicate_template_id=duplicate["id"], canonical_template_id=canonical["id"],
                        definition_hash=digest, reason="exact-definition-duplicate"))
                connection.execute(TemplateVersion.__table__.delete().where(
                    TemplateVersion.template_id == duplicate["id"]))
                connection.execute(Template.__table__.delete().where(Template.id == duplicate["id"]))
                store.delete(duplicate["object_key"])
    engine.dispose()
    return {"groups": len(groups_seen), "duplicates": duplicate_count, "applied": apply, "items": groups_seen}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the cleanup; otherwise audit only")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "template-dedupe-report.json")
    args = parser.parse_args()
    result = run(args.apply)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['groups']} exact duplicate groups; {result['duplicates']} removable templates; applied={result['applied']}")
