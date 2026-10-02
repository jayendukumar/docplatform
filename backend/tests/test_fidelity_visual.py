"""E16 raster comparison regression tests (DD-420). Requires the optional fidelity extra (DD-419)."""
import struct
import sys
import zlib
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fidelity import visual
from tests.test_fidelity import make_pdf

pytestmark = pytest.mark.skipif(visual.rasterizer_status() != "available",
                                reason="pypdfium2 fidelity extra is not installed")

TEXT = "BT /F1 24 Tf 72 700 Td (Fidelity harness) Tj ET 72 600 300 2 re f"


def test_identical_documents_match_exactly():
    pdf = make_pdf(TEXT)
    report = visual.compare_visual(pdf, pdf)
    page = report["pages"][0]
    assert report["contract"] == "fidelity-visual-v1" and report["status"] == "compared"
    assert page["exact_iou"] == 1.0 and page["tolerant"] == {"recall": 1.0, "precision": 1.0, "f1": 1.0}
    assert page["worst_cells"] == [] and report["summary"]["page_f1"]["pages_below_0_5"] == []


def test_small_shift_is_within_tolerance_but_not_exact():
    shifted = make_pdf("BT /F1 24 Tf 73.4 700 Td (Fidelity harness) Tj ET 73.4 600 300 2 re f")  # 0.5 mm
    report = visual.compare_visual(make_pdf(TEXT), shifted, tolerance_mm=1.0)
    page = report["pages"][0]
    assert page["exact_iou"] < 0.9
    assert page["tolerant"]["f1"] > 0.97


def test_large_shift_is_localised_to_cells_and_scores_zero_when_disjoint():
    moved = make_pdf("BT /F1 24 Tf 72 400 Td (Fidelity harness) Tj ET")
    report = visual.compare_visual(make_pdf(TEXT), moved)
    page = report["pages"][0]
    assert page["tolerant"]["f1"] == 0.0
    assert report["summary"]["page_f1"]["pages_below_0_5"] == [1]
    # The moved 24 pt line sits at 392 pt (138.3 mm) from the top; at 72 dpi cells form a 9.88 mm grid.
    assert {tuple(cell["box_mm"][1::2]) for cell in page["worst_cells"]} == {(128.4, 138.3)}
    assert all(cell["extra_px"] > 0 and cell["missing_px"] == 0 for cell in page["worst_cells"])
    assert page["tolerant"]["recall"] == 0.0


def test_page_count_mismatch_is_reported():
    writer = PdfWriter()
    for _ in range(2):
        writer.add_page(PdfReader(BytesIO(make_pdf(TEXT))).pages[0])
    two_pages = BytesIO()
    writer.write(two_pages)
    report = visual.compare_visual(two_pages.getvalue(), make_pdf(TEXT))
    assert report["summary"]["pages_compared"] == 1
    assert report["pages"][1] == {"page_number": 2, "status": "missing-in-candidate"}


def test_diff_image_is_a_valid_indexed_png(tmp_path):
    report = visual.compare_visual(make_pdf(TEXT), make_pdf("BT /F1 24 Tf 72 400 Td (Moved) Tj ET"),
                                   diff_dir=tmp_path)
    image = Path(report["pages"][0]["diff_image"]).read_bytes()
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, depth, color_type = struct.unpack(">IIBB", image[16:26])
    assert (width, height, depth, color_type) == (612, 792, 8, 3)
    idat = image.index(b"IDAT")
    length = struct.unpack(">I", image[idat - 4:idat])[0]
    raw = zlib.decompress(image[idat + 4:idat + 4 + length])
    assert len(raw) == height * (width + 1)
    assert {1, 2} <= set(raw)  # both missing (red) and extra (blue) ink are present


def test_unavailable_rasterizer_is_reported(monkeypatch):
    monkeypatch.setattr(visual, "rasterizer_status", lambda: "unavailable-no-rasterizer")
    report = visual.compare_visual(b"", b"")
    assert report["status"] == "unavailable-no-rasterizer" and report["summary"] is None


def test_dpi_is_bounded():
    with pytest.raises(ValueError, match="dpi"):
        visual.compare_visual(make_pdf(TEXT), make_pdf(TEXT), dpi=1000)
