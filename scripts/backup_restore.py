"""Create or restore a local, explicit backup of database and object storage."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path


def _safe_extract(bundle: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in bundle.getmembers():
        target = (root / member.name).resolve()
        if target != root and root not in target.parents:
            raise ValueError("backup contains a path outside the object directory")
    bundle.extractall(root, filter="data")


def create_backup(archive: Path, objects: Path, database_url: str) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    dump_path = archive.with_suffix(".dump")
    subprocess.run(["pg_dump", "--format=custom", "--file", str(dump_path), database_url], check=True)
    if not dump_path.is_file():
        raise ValueError("pg_dump did not create the database dump")
    manifest = {
        "format": "docplatform-backup-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "database_dump": {"filename": dump_path.name, "sha256": hashlib.sha256(dump_path.read_bytes()).hexdigest()},
    }
    with tarfile.open(archive, "w:gz") as bundle:
        if objects.exists():
            bundle.add(objects, arcname="objects", recursive=True)
        info = json.dumps(manifest, indent=2).encode()
        member = tarfile.TarInfo("manifest.json")
        member.size = len(info)
        import io
        bundle.addfile(member, io.BytesIO(info))
def restore_backup(archive: Path, objects: Path, database_url: str) -> None:
    with tarfile.open(archive, "r:gz") as bundle:
        manifest_file = bundle.extractfile("manifest.json")
        if manifest_file is None:
            raise ValueError("backup manifest is missing")
        manifest = json.loads(manifest_file.read())
        if manifest.get("format") != "docplatform-backup-v1":
            raise ValueError("unsupported backup format")
        dump_path = archive.with_suffix(".dump")
        dump_manifest = manifest.get("database_dump")
        if isinstance(dump_manifest, dict) and dump_manifest.get("sha256"):
            if not dump_path.is_file():
                raise ValueError("database dump is missing")
            actual = hashlib.sha256(dump_path.read_bytes()).hexdigest()
            if actual != dump_manifest["sha256"]:
                raise ValueError("database dump checksum does not match the backup manifest")
        _safe_extract(bundle, objects.parent)
    subprocess.run(["pg_restore", "--clean", "--if-exists", "--dbname", database_url,
                    str(dump_path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("archive", type=Path)
    create.add_argument("--objects", type=Path, default=Path("data/objects"))
    create.add_argument("--database-url", required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--objects", type=Path, default=Path("data/objects"))
    restore.add_argument("--database-url", required=True)
    args = parser.parse_args()
    if args.action == "create":
        create_backup(args.archive, args.objects, args.database_url)
    else:
        restore_backup(args.archive, args.objects, args.database_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
