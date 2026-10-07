from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.audit_isda_template import audit
from scripts.audit_isda_review_checklist import audit as audit_review_checklist


def test_isda_contract_audit_passes() -> None:
    result = audit()

    assert result["status"] == "pass"
    assert result["object_count"] == 381
    assert result["anchor_count"] == 381
    assert result["page_count"] == 36
    assert result["table_count"] == 2
    assert result["rendered_page_surface_count"] == 36
    assert result["missing_fields"] == []
    assert result["bound_field_count"] == 147
    assert result["semantic_kind_counts"] == {"clause": 220, "field": 143, "schedule": 10, "signature": 8}
    assert result["semantic_kind_counts"]["signature"] == 8
    assert result["page_semantic_kind_counts"]["25"]["clause"] == 6
    assert result["page_semantic_kind_counts"]["26"]["clause"] == 6
    assert result["page_semantic_kind_counts"]["27"]["clause"] == 7
    assert result["page_semantic_kind_counts"]["28"]["signature"] == 4
    assert result["page_semantic_kind_counts"]["36"]["signature"] == 4
    assert result["page_semantic_kind_counts"]["32"]["schedule"] == 2
    assert all(result["page_semantic_kind_counts"][str(page)]["field"] > 0 for page in range(28, 37))
    assert all(result["page_semantic_kind_counts"][str(page)]["schedule"] > 0 for page in (29, 31, 32, 33, 34, 35, 36))
    assert all(table["sample_row_count"] == 2 for table in result["tables"])
    assert result["failures"] == []


def test_isda_review_checklist_provenance_matches_current_candidate() -> None:
    result = audit_review_checklist(
        REPOSITORY_ROOT / "docs" / "isda-review-evidence-checklist.md",
        REPOSITORY_ROOT / "artifacts" / "isda-foreground-baseline" / "isda-foreground.json",
        REPOSITORY_ROOT / "artifacts" / "isda-editable-comparison.json",
    )

    assert result["status"] == "pass"
    assert result["candidate_object_count"] == 381
    assert result["failures"] == []
