"""Audit that every source-backlog Must story has an explicit UI status."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STORY_RE = re.compile(r"^\|\s*(E\d+-\d+)\s*\|.*\|\s*Must\s*\|")
STATUS_RE = re.compile(r"['\"](E\d+-\d+)['\"]\s*:\s*['\"](implemented|partial|planned)['\"]")


def audit(epics: Path, status_file: Path) -> dict[str, object]:
    must_ids = [match.group(1) for line in epics.read_text(encoding="utf-8").splitlines()
                if (match := STORY_RE.match(line))]
    statuses = {match.group(1): match.group(2)
                for match in STATUS_RE.finditer(status_file.read_text(encoding="utf-8"))}
    missing = [story_id for story_id in must_ids if story_id not in statuses]
    counts = {status: sum(value == status for value in statuses.values())
              for status in ("implemented", "partial", "planned")}
    return {
        "contract": "must-story-status-audit-v1",
        "must_story_count": len(must_ids),
        "status_count": len(statuses),
        "must_status_counts": {status: sum(statuses.get(story_id) == status for story_id in must_ids)
                                for status in counts},
        "missing_must_ids": missing,
        "all_must_ids_explicit": not missing,
        "statuses": {story_id: statuses[story_id] for story_id in must_ids if story_id in statuses},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epics", type=Path, default=Path("docs/epics.md"))
    parser.add_argument("--status", type=Path, default=Path("frontend/src/storyStatus.ts"))
    args = parser.parse_args()
    report = audit(args.epics, args.status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_must_ids_explicit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
