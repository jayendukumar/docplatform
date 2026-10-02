import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from pypdf import PdfWriter

from scripts.compare_isda_candidate import (
    page_size_mismatches,
    page_sizes,
    page_text_metrics,
    candidate_manifest_status,
    visual_comparison_status,
)


def test_page_text_metrics_preserve_page_alignment_and_missing_pages() -> None:
    metrics = page_text_metrics(["alpha", "beta"], ["alpha", "different", "extra"])

    assert [metric["page"] for metric in metrics] == [1, 2, 3]
    assert metrics[0]["similarity"] == 1.0
    assert metrics[1]["source_chars"] == 4
    assert metrics[2]["source_chars"] == 0
    assert metrics[2]["candidate_chars"] == 5
    assert metrics[2]["similarity"] == 0.0


def test_page_sizes_report_every_page_geometry(tmp_path) -> None:
    path = tmp_path / "geometry.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)

    from pypdf import PdfReader

    assert page_sizes(PdfReader(str(path))) == [[612.0, 792.0], [612.0, 792.0]]
    assert page_size_mismatches([[612.0, 792.0]], [[612.0, 792.0], [600.0, 800.0]]) == [
        {"page": 2, "source": None, "candidate": [600.0, 800.0]}
    ]


def test_visual_comparison_status_is_explicitly_non_approval() -> None:
    assert visual_comparison_status() in {
        "unavailable-no-local-rasterizer",
        "not-run-rasterizer-not-integrated",
    }


def test_candidate_manifest_requires_foreground_only_boundary(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"locked_background":"omitted","objects":347}', encoding="utf-8")
    result = candidate_manifest_status(manifest)
    assert result["status"] == "foreground-only"
    assert result["object_count"] == 347
    manifest.write_text('{"locked_background":"merged"}', encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="locked_background=omitted"):
        candidate_manifest_status(manifest)
    manifest.write_text('{"locked_background":"omitted","objects":0}', encoding="utf-8")
    with pytest.raises(ValueError, match="positive semantic object count"):
        candidate_manifest_status(manifest)
