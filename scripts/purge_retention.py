"""Purge files older than an explicit retention period from local object storage."""
from __future__ import annotations

import argparse
import time
from pathlib import Path


def expired_files(root: Path, cutoff: float) -> list[Path]:
    """Return regular files eligible for purge, never symlink targets."""
    return sorted(
        (path for path in root.rglob("*")
         if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff),
        key=lambda path: path.as_posix(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--days", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.days < 1: parser.error("--days must be at least 1")
    if not args.root.is_dir(): parser.error("root must be an existing directory")
    cutoff = time.time() - args.days * 86400
    for path in expired_files(args.root, cutoff):
        print(path)
        if not args.dry_run: path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
