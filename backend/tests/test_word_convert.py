import io
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.word_convert import (
    WordConversionError,
    WordConversionUnavailable,
    convert_docx_to_pdf,
    patch_pdf_metadata,
)


def _docx() -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", b"<Types/>")
        package.writestr("word/document.xml", b"<document/>")
    return output.getvalue()


def _pdf() -> bytes:
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Count 0 /Kids [] >>"]
    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, value in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend("".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def test_conversion_boundary_runs_configured_command_and_validates_pdf(monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_DB_PASSWORD", "secret")
    command = [sys.executable, "-c",
               "import os,pathlib,sys; assert 'DOCPLATFORM_DB_PASSWORD' not in os.environ; assert pathlib.Path.cwd().name.startswith('docplatform-word-'); assert __import__('socket').socket.connect.__module__ == 'sitecustomize'; sys.stderr.write('x' * (8 * 1024 * 1024)); pathlib.Path(sys.argv[2]).write_bytes(b'%PDF-1.7\\n')"]
    output, report = convert_docx_to_pdf(_docx(), command, 2, 1024)
    assert output.startswith(b"%PDF-1.7")
    assert report["status"] == "candidate"


def test_conversion_is_explicitly_unavailable_without_engine():
    with pytest.raises(WordConversionUnavailable, match="not configured"):
        convert_docx_to_pdf(_docx(), [], 2, 1024)


def test_conversion_rejects_non_pdf_output():
    command = [sys.executable, "-c",
               "import pathlib,sys; pathlib.Path(sys.argv[2]).write_bytes(b'not-pdf')"]
    with pytest.raises(WordConversionError, match="invalid PDF"):
        convert_docx_to_pdf(_docx(), command, 2, 1024)


def test_conversion_kills_timed_out_engine_group():
    command = [sys.executable, "-c", "import time; time.sleep(10)"]
    with pytest.raises(WordConversionError, match="exceeded its time limit"):
        convert_docx_to_pdf(_docx(), command, 1, 1024)


def test_pdf_metadata_patch_records_title_author_and_language():
    output = patch_pdf_metadata(_pdf(), {"title": "Report", "author": "Ada", "language": "de-DE"})
    assert b"/Title <FEFF005200650070006F00720074>" in output
    assert b"/Author <FEFF004100640061>" in output
    assert b"/Lang <FEFF00640065002D00440045>" in output
