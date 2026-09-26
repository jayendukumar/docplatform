"""Shell-free DOCX-to-PDF conversion boundary for an operator-provided engine."""
from __future__ import annotations

import base64
import re
import subprocess
import tempfile
from pathlib import Path

from app.process_sandbox import run_engine_command, sandbox_environment
from app.security import validate_pdf_active_content
from app.word_merge import WordMergeError, validate_docx_package


class WordConversionError(RuntimeError):
    pass


class WordConversionUnavailable(WordConversionError):
    pass


def _pdf_text(value: str) -> str:
    encoded = value.encode("utf-16-be")
    return "<FEFF" + encoded.hex().upper() + ">"


def patch_pdf_metadata(pdf: bytes, metadata: dict[str, str]) -> bytes:
    """Append bounded Info/Catalog metadata to a conventional PDF candidate."""
    if not isinstance(metadata, dict) or any(not isinstance(value, str) or len(value) > 500
                                             for value in metadata.values()):
        raise WordConversionError("PDF metadata values are invalid")
    required = ("title", "author", "language")
    if any(key not in metadata for key in required):
        raise WordConversionError("PDF metadata requires title, author, and language")
    source = pdf.decode("latin-1")
    start_match = re.search(r"startxref\s+(\d+)\s+%%EOF\s*$", source)
    if not start_match:
        raise WordConversionError("PDF has no terminal startxref")
    trailer_start = source.rfind("trailer", 0, start_match.start())
    trailer = source[trailer_start:start_match.start()]
    size_match = re.search(r"/Size\s+(\d+)", trailer)
    root_match = re.search(r"/Root\s+(\d+\s+0\s+R)", trailer)
    if not size_match or not root_match:
        raise WordConversionError("PDF trailer lacks size or root")
    root_reference = root_match.group(1)
    root_number = int(root_reference.split()[0])
    root_start = source.find(f"{root_number} 0 obj")
    root_end = source.find("endobj", root_start)
    root = source[root_start:root_end]
    pages_match = re.search(r"/Pages\s+(\d+\s+0\s+R)", root)
    if root_start < 0 or root_end < 0 or not pages_match:
        raise WordConversionError("PDF catalog lacks pages")
    size = int(size_match.group(1))
    info_id, catalog_id = size, size + 1
    info = (f"{info_id} 0 obj\n<< /Title {_pdf_text(metadata['title'])} "
            f"/Author {_pdf_text(metadata['author'])} >>\nendobj\n")
    catalog = (f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_match.group(1)} "
               f"/Lang {_pdf_text(metadata['language'])} /ViewerPreferences "
               f"<< /DisplayDocTitle true >> >>\nendobj\n")
    prefix = source if source.endswith("\n") else source + "\n"
    info_offset = len(prefix.encode("latin-1"))
    catalog_offset = info_offset + len(info.encode("latin-1"))
    xref_offset = catalog_offset + len(catalog.encode("latin-1"))
    xref = (f"xref\n{info_id} 2\n{info_offset:010d} 00000 n \n"
            f"{catalog_offset:010d} 00000 n \n")
    trailer = (f"trailer\n<< /Size {size + 2} /Root {catalog_id} 0 R /Info {info_id} 0 R "
               f"/Prev {start_match.group(1)} >>\nstartxref\n{xref_offset}\n%%EOF\n")
    return (prefix + info + catalog + xref + trailer).encode("latin-1")


def convert_docx_to_pdf(docx: bytes, command: list[str], timeout_seconds: int,
                        max_output_bytes: int, metadata: dict[str, str] | None = None
                        ) -> tuple[bytes, dict[str, object]]:
    """Run a configured converter as ``command input.docx output.pdf``."""
    if not command:
        raise WordConversionUnavailable("Word-to-PDF converter is not configured")
    if not all(isinstance(part, str) and part for part in command):
        raise WordConversionError("Word-to-PDF converter configuration is invalid")
    try:
        validate_docx_package(docx)
    except WordMergeError as exc:
        raise WordConversionError(str(exc)) from None
    with tempfile.TemporaryDirectory(prefix="docplatform-word-") as directory:
        root = Path(directory)
        source = root / "input.docx"
        target = root / "output.pdf"
        source.write_bytes(docx)
        environment = sandbox_environment(directory)
        try:
            returncode = run_engine_command([*command, str(source), str(target)],
                                            environment=environment, cwd=directory,
                                            timeout_seconds=timeout_seconds)
        except subprocess.TimeoutExpired:
            raise WordConversionError("Word-to-PDF converter exceeded its time limit") from None
        except OSError:
            raise WordConversionError("Word-to-PDF converter could not be executed") from None
        if returncode != 0:
            raise WordConversionError("Word-to-PDF converter rejected the document")
        if not target.is_file():
            raise WordConversionError("Word-to-PDF converter did not produce a PDF")
        output = target.read_bytes()
    if len(output) > max_output_bytes:
        raise WordConversionError("converted PDF exceeds the configured output limit")
    if not output.startswith(b"%PDF-"):
        raise WordConversionError("Word-to-PDF converter produced an invalid PDF")
    report_metadata: object = "not assessed"
    if metadata is not None:
        output = patch_pdf_metadata(output, metadata)
        report_metadata = metadata
        if len(output) > max_output_bytes:
            raise WordConversionError("converted PDF exceeds the configured output limit")
    try:
        validate_pdf_active_content(output)
    except ValueError as exc:
        raise WordConversionError(str(exc)) from None
    return output, {"engine": "configured-word-converter", "status": "candidate",
                    "output_bytes": len(output), "metadata": report_metadata}


def encode_pdf(output: bytes) -> str:
    return base64.b64encode(output).decode("ascii")
