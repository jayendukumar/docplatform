import base64
import io
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base
from app.storage import LocalStore
from app.word_merge import WordMergeError, merge_docx

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(document: str, extra: dict[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", b"<Types/>")
        package.writestr("word/document.xml", document.encode())
        for name, content in (extra or {}).items():
            package.writestr(name, content)
    return output.getvalue()


def test_docx_merge_replaces_scalar_and_repeated_table_tokens():
    template = _docx('''<w:document xmlns:w="NS"><w:body>
      <w:p><w:r><w:t>Hello {{customer.name}}</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>{{#items}} {{item.name}} {{/items}}</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>'''.replace("NS", W_NS))
    merged, report = merge_docx(template, {"customer": {"name": "Ada"}, "items": [{"name": "A"}, {"name": "B"}]})
    with ZipFile(io.BytesIO(merged)) as package:
        xml = package.read("word/document.xml").decode()
    assert "Hello Ada" in xml and "A" in xml and "B" in xml
    assert report["engine"] == "docx-merge-v1"


@pytest.mark.parametrize("template", [b"not zip", _docx("<bad")])
def test_docx_merge_rejects_malformed_packages(template):
    with pytest.raises(WordMergeError):
        merge_docx(template, {})


def test_docx_merge_rejects_external_relationships():
    template = _docx(f'<w:document xmlns:w="{W_NS}"/>', {
        "word/_rels/document.xml.rels": b'<Relationship TargetMode="External" Target="https://example.test"/>'})
    with pytest.raises(WordMergeError, match="external"):
        merge_docx(template, {})


def test_word_merge_api_returns_bounded_docx(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    template = _docx('''<w:document xmlns:w="NS"><w:body><w:p><w:r><w:t>{{name}}</w:t></w:r></w:p></w:body></w:document>'''.replace("NS", W_NS))
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        response = client.post("/api/word/merge", json={
            "template_base64": base64.b64encode(template).decode("ascii"), "data": {"name": "Ada"},
        })
    assert response.status_code == 200, response.text
    merged = base64.b64decode(response.json()["document_base64"])
    assert b"Ada" in ZipFile(io.BytesIO(merged)).read("word/document.xml")
