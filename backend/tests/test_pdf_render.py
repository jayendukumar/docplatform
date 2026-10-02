import sys
import base64
import re
import zlib
from io import BytesIO

import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.pdf_render import PdfRenderError, PdfRenderUnavailable, render_html_to_pdf
from app.pdf_background import PdfBackgroundError, merge_pdf_background
from app.pdf_toc import add_page_numbers, add_toc_page_numbers
from app.renderer_adapter import default_command
from app.rendering import render_definition
from app.storage import LocalStore


def _pdf() -> bytes:
    body = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    first = len(b"%PDF-1.4\n")
    second = first + body.index(b"2 0 obj")
    xref_offset = first + len(body)
    return (b"%PDF-1.4\n" + body + f"xref\n0 3\n0000000000 65535 f \n{first:010d} 00000 n \n{second:010d} 00000 n \n"
            f"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())


def _command() -> list[str]:
    return [sys.executable, "-c", f"import os,pathlib,socket,sys; assert pathlib.Path.cwd().name.startswith('docplatform-pdf-'); assert socket.socket.connect.__module__ == 'sitecustomize'; assert 'DOCPLATFORM_DB_PASSWORD' not in os.environ; sys.stderr.write('x' * (8 * 1024 * 1024)); pathlib.Path(sys.argv[2]).write_bytes({_pdf()!r})"]


def _image_command() -> list[str]:
    return [sys.executable, "-c", f"import pathlib,sys; assert 'data:image/png;base64,' in pathlib.Path(sys.argv[1]).read_text(); pathlib.Path(sys.argv[2]).write_bytes({_pdf()!r})"]


def _centered_image_command() -> list[str]:
    return [sys.executable, "-c", f"import pathlib,sys; html=pathlib.Path(sys.argv[1]).read_text(); assert '<figure class=\"template-image image-align-center\" style=\"text-align:center\">' in html; assert 'style=\"display:block;margin-left:auto;margin-right:auto;' in html; pathlib.Path(sys.argv[2]).write_bytes({_pdf()!r})"]


def _blank_pdf() -> bytes:
    from pypdf import PdfWriter
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def _sized_blank_pdf(width: float, height: float) -> bytes:
    from pypdf import PdfWriter
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    writer.write(output)
    return output.getvalue()


def test_pdf_background_is_scaled_behind_each_foreground_page():
    merged = merge_pdf_background(_blank_pdf(), _blank_pdf(), max_bytes=1_000_000)
    from pypdf import PdfReader
    assert len(PdfReader(BytesIO(merged)).pages) == 1
    with pytest.raises(PdfBackgroundError, match="must be PDF"):
        merge_pdf_background(b"not-pdf", _blank_pdf(), max_bytes=1_000_000)


@pytest.mark.parametrize("foreground_size", [(612, 792), (792, 612), (841.89, 595.28)])
def test_pdf_background_preserves_foreground_geometry_across_page_sizes(foreground_size):
    merged = merge_pdf_background(_sized_blank_pdf(*foreground_size), _sized_blank_pdf(612, 792), max_bytes=1_000_000)
    from pypdf import PdfReader
    page = PdfReader(BytesIO(merged), strict=True).pages[0]
    assert float(page.mediabox.width) == pytest.approx(foreground_size[0], abs=0.01)
    assert float(page.mediabox.height) == pytest.approx(foreground_size[1], abs=0.01)
    assert page.get_contents() is not None


def test_configured_designer_renderer_returns_candidate_pdf():
    output, report = render_html_to_pdf("<html lang='en'><title>Invoice</title></html>", _command(), 2, 10_000,
                                       {"title": "Invoice", "author": "Ada", "language": "en-US"})
    assert output.startswith(b"%PDF-")
    assert report["status"] == "candidate"
    assert report["metadata"] == {"title": "Invoice", "author": "Ada", "language": "en-US"}


def test_designer_renderer_is_explicitly_unavailable_by_default():
    with pytest.raises(PdfRenderUnavailable, match="not configured"):
        render_html_to_pdf("<p>hello</p>", [], 2, 10_000,
                           {"title": "x", "author": "", "language": "en"})


def test_designer_renderer_rejects_non_pdf_output():
    command = [sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[2]).write_bytes(b'nope')"]
    with pytest.raises(PdfRenderError, match="invalid PDF"):
        render_html_to_pdf("<p>hello</p>", command, 2, 10_000,
                           {"title": "x", "author": "", "language": "en"})


def test_designer_renderer_kills_timed_out_engine_group():
    command = [sys.executable, "-c", "import time; time.sleep(10)"]
    with pytest.raises(PdfRenderError, match="exceeded its time limit"):
        render_html_to_pdf("<p>hello</p>", command, 1, 10_000,
                           {"title": "x", "author": "", "language": "en"})


def test_render_pdf_endpoint_runs_renderer_inside_worker_boundary(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(pdf_renderer_command=_command())
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "PDF test", "definition": {
            "name": "PDF test", "blocks": [{"type": "text", "text": "Hello"}]}}).json()
        response = client.post(f"/api/templates/{created['id']}/render-pdf", json={})
        assert response.status_code == 200, response.text
        assert response.json()["report"]["status"] == "candidate"
        assert response.json()["report"]["render_locale"] == "en"
        assert response.json()["report"]["locked_background"] == "omitted"
        document = response.json()["document_base64"]
        assert document.startswith("JVBER")
        assert response.json()["report"]["output_bytes"] == len(base64.b64decode(document))


def test_render_pdf_uses_its_own_bounded_block_limit(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(pdf_renderer_command=_command(), sync_pdf_render_max_blocks=2)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "PDF limit", "definition": {
            "name": "PDF limit", "blocks": [{"type": "text", "text": str(index)} for index in range(3)]}}).json()
        response = client.post(f"/api/templates/{created['id']}/render-pdf", json={})
        assert response.status_code == 413
        assert response.json()["detail"] == "template exceeds the synchronous PDF render block limit"


def test_render_pdf_editable_only_comparison_omits_locked_background(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(pdf_renderer_command=_command())
    background = "data:application/pdf;base64," + base64.b64encode(_pdf()).decode("ascii")
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "Editable comparison", "definition": {
            "name": "Editable comparison", "page": {"background_pdf": background},
            "blocks": [{"type": "text", "text": "Editable foreground"}],
        }}).json()
        response = client.post(f"/api/templates/{created['id']}/render-pdf", json={"comparison_mode": "editable-only"})
        assert response.status_code == 200, response.text
        assert response.json()["report"]["locked_background"] == "omitted"


def test_render_pdf_endpoint_stages_uploaded_asset_into_network_disabled_input(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    asset_name = "0123456789abcdef0123456789abcdef.png"
    store.put(f"assets/{asset_name}", b"\x89PNG\r\n\x1a\nfixture")
    settings = Settings(pdf_renderer_command=_image_command())
    with TestClient(create_app(settings=settings, engine=engine, store=store, frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "Logo PDF", "definition": {
            "name": "Logo PDF", "blocks": [{"type": "image", "src": f"/api/assets/{asset_name}"}]}}).json()
        response = client.post(f"/api/templates/{created['id']}/render-pdf", json={})
        assert response.status_code == 200, response.text


def test_render_pdf_endpoint_passes_centered_image_layout_to_pdf_engine(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(pdf_renderer_command=_centered_image_command())
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        created = client.post("/api/templates", json={"name": "Centered image PDF", "definition": {
            "name": "Centered image PDF", "blocks": [{"type": "image", "src": "data:image/png;base64,AA==", "align": "center"}]}}).json()
        response = client.post(f"/api/templates/{created['id']}/render-pdf", json={})
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("alignment", ["left", "center", "right"])
def test_real_chromium_pdf_places_image_at_requested_content_alignment(alignment):
    html = render_definition({"blocks": [{
        "type": "image",
        "src": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
        "align": alignment,
        "width": 120,
    }]})["artifact"]
    pdf, report = render_html_to_pdf(html, default_command("chromium"), 60, 10_000_000,
                                     {"title": f"{alignment} image", "author": "", "language": "en"})
    assert report["engine"] == "chromium"
    streams = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        try:
            streams.append(zlib.decompress(match.group(1)).decode("latin1"))
        except zlib.error:
            continue
    content = next(stream for stream in streams if "/X4 Do" in stream)
    clip = re.search(r"(?P<x>[\d.]+) (?P<y>[\d.]+) (?P<width>[\d.]+) (?P<height>[\d.]+) re\s+W\* n", content)
    image = re.search(r"(?P<width>[\d.]+) 0 0 -(?P<height>[\d.]+) (?P<x>[\d.]+) (?P<y>[\d.]+) cm\s+0 0 0 RG", content)
    assert clip and image
    clip_x = float(clip["x"])
    available = float(clip["width"]) - float(image["width"])
    expected_x = clip_x + {"left": 0, "center": available / 2, "right": available}[alignment]
    # Chromium rounds the CSS-to-PDF transform; the remaining error is below 1 CSS pixel.
    assert abs(float(image["x"]) - expected_x) < 3


def test_real_chromium_pdf_keeps_toc_link_target_for_declared_anchor():
    html = render_definition({"blocks": [
        {"type": "toc"},
        {"type": "text", "text": "Before the section", "break_before": True},
        {"type": "text", "text": "Introduction", "anchor_id": "intro",
         "toc_label": "Introduction", "toc_level": 1},
    ]})["artifact"]
    pdf, report = render_html_to_pdf(html, default_command("chromium"), 60, 10_000_000,
                                     {"title": "TOC", "author": "", "language": "en"})
    assert report["engine"] == "chromium"
    pdf = add_toc_page_numbers(pdf, 10_000_000)
    rendered_reader = PdfReader(BytesIO(pdf))
    assert "2" in (rendered_reader.pages[0].extract_text() or "")
    annotations = [annotation.get_object() for page in rendered_reader.pages
                    for annotation in (page.get("/Annots") or [])]
    assert any(annotation.get("/Subtype") == "/Link" and annotation.get("/Dest") == "/intro"
               for annotation in annotations)


def test_real_chromium_pdf_repeats_table_header_and_keeps_rows_together():
    html = render_definition({
        "blocks": [
            {"type": "text", "text": "\n".join(["FILLER LINE"] * 35)},
            {"type": "table", "items": "rows", "columns": [
                {"header": "Description", "path": "description", "format": "text"},
                {"header": "Amount", "path": "amount", "format": "currency"},
            ]},
        ],
        "sample_data": {"rows": [
            {"description": "ROW-ONE " + ("detail " * 12), "amount": 1.0},
            {"description": "ROW-TWO " + ("detail " * 12), "amount": 2.0},
        ]},
    })["artifact"]
    pdf, report = render_html_to_pdf(html, default_command("chromium"), 60, 10_000_000,
                                     {"title": "Flow", "author": "", "language": "en"})
    assert report["engine"] == "chromium"
    pages = [page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages]
    assert len(pages) == 2
    assert all(page.count("Description") == 1 for page in pages)
    assert "ROW-ONE" in pages[0] and "ROW-ONE" not in pages[1]
    assert "ROW-TWO" not in pages[0] and "ROW-TWO" in pages[1]


def test_page_number_overlay_uses_physical_page_index_and_preserves_metadata():
    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Numbered fixture", "/Author": "DocPlatform"})
    writer.write(output)
    numbered = add_page_numbers(output.getvalue(), 20, 20, 1_000_000)
    reader = PdfReader(BytesIO(numbered))
    assert reader.metadata["/Title"] == "Numbered fixture"
    assert "1" in (reader.pages[0].extract_text() or "")
    assert "2" in (reader.pages[1].extract_text() or "")


def test_page_number_overlay_is_isolated_from_a_leaked_content_transform():
    # DD-429: Chromium leaves a scaling/flipping CTM active; without q/Q isolation the overlay was ~2 pt at top-left.
    import sys
    from pathlib import Path

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from fidelity.source_model import analyse_pdf

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    leaked = DecodedStreamObject()
    leaked.set_data(b"0.24 0 0 -0.24 0 792 cm")  # transform left active, as Chromium does
    page[NameObject("/Contents")] = writer._add_object(leaked)
    output = BytesIO()
    writer.write(output)
    numbered = analyse_pdf(add_page_numbers(output.getvalue(), 20, 20, 1_000_000))
    (word,) = numbered["pages"][0]["words"]
    assert word["text"] == "1" and word["size_pt"] == 9
    assert word["y_mm"] > 260 and word["x_mm"] > 150
