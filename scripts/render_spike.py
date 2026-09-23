"""Run the E4-01 candidate comparison without external network or model calls."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.rendering import compare_candidates  # noqa: E402


def main():
    fixtures = [{"name": "script-matrix", "locale": "en", "blocks": [{"type": "text", "text":
        "Arabic العربية Hebrew עברית Hindi हिन्दी Tamil தமிழ் Thai ไทย Chinese 中文 Japanese 日本語"}]}]
    print(json.dumps(compare_candidates(fixtures), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
