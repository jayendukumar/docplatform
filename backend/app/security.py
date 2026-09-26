"""Upload security hooks with bounded, shell-free external scanner execution."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import zlib
from pathlib import Path

from app.process_sandbox import run_engine_command


class UploadScanError(RuntimeError):
    pass


_PDF_ACTIVE_CONTENT_RE = re.compile(
    rb"/(?:JavaScript|JS|AA|OpenAction|Launch|EmbeddedFile|RichMedia|XFA)(?=\s|/|\[|<|>)",
    re.IGNORECASE,
)
_PDF_NAME_RE = re.compile(rb"/([A-Za-z0-9#]+)")
_PDF_FLATE_STREAM_RE = re.compile(rb"/Filter\s*/FlateDecode(?:(?!endobj).){0,1024}?stream\r?\n", re.DOTALL)
_PDF_MAX_COMPRESSED_STREAM = 1_000_000
_PDF_MAX_DECOMPRESSED_STREAM = 4_000_000
_PDF_MAX_DECOMPRESSED_TOTAL = 16_000_000
_SCANNER_ENV_NAMES = frozenset({
    "LANG", "LC_ALL", "LC_CTYPE", "PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "TZ",
})


def validate_pdf_active_content(data: bytes) -> None:
    """Reject common PDF actions and embedded active-content declarations.

    This is a bounded lexical gate before storage, not a complete PDF parser or
    malware scanner. Compressed/object-obfuscated content still requires the
    optional scanner and isolated downstream parser boundary.
    """
    sources = [data]
    total = 0
    for match in _PDF_FLATE_STREAM_RE.finditer(data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        compressed = data[start:end].rstrip(b"\r\n")
        if not compressed or len(compressed) > _PDF_MAX_COMPRESSED_STREAM:
            continue
        try:
            decoder = zlib.decompressobj()
            inflated = decoder.decompress(compressed, _PDF_MAX_DECOMPRESSED_STREAM + 1)
            if not decoder.eof or len(inflated) > _PDF_MAX_DECOMPRESSED_STREAM:
                continue
            inflated += decoder.flush()
        except zlib.error:
            continue
        if len(inflated) > _PDF_MAX_DECOMPRESSED_STREAM or total + len(inflated) > _PDF_MAX_DECOMPRESSED_TOTAL:
            continue
        total += len(inflated)
        sources.append(inflated)
    def decoded_pdf_names(source: bytes) -> bytes:
        def decode_name(match: re.Match[bytes]) -> bytes:
            name = re.sub(rb"#([0-9A-Fa-f]{2})", lambda item: bytes.fromhex(item.group(1).decode("ascii")),
                          match.group(1))
            return b"/" + name

        return _PDF_NAME_RE.sub(decode_name, source)

    if any(_PDF_ACTIVE_CONTENT_RE.search(decoded_pdf_names(source)) for source in sources):
        raise ValueError("PDF contains unsupported active content")


def validate_svg_markup(data: bytes) -> None:
    """Reject active or externally-referencing SVG markup before storage/use."""
    try:
        markup = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("SVG image must be valid UTF-8") from None
    if len(data) > 1_000_000:
        raise ValueError("SVG image is too large")
    if not re.search(r"<\s*svg(?:\s|>)", markup, re.IGNORECASE) or not re.search(r"</\s*svg\s*>", markup, re.IGNORECASE):
        raise ValueError("SVG image must contain a root svg element")
    if re.search(r"<\s*(?:script|foreignObject)|<\s*!DOCTYPE|<\s*!ENTITY|\bon[a-z]+\s*=|javascript:|url\s*\(|(?:xlink:)?href\s*=\s*['\"]\s*(?:https?:|//)", markup, re.IGNORECASE):
        raise ValueError("SVG image contains unsafe markup or external references")


def scan_upload(data: bytes, command: list[str], timeout_seconds: int) -> None:
    """Run an optional scanner; zero exit means clean, anything else rejects."""
    if not command:
        return
    if not all(isinstance(part, str) and part for part in command):
        raise UploadScanError("upload scanner configuration is invalid")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="docplatform-scan-", suffix=".upload", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Scanner commands are deployment-provided executables. Give them only
        # process discovery, temporary-directory, and locale settings; do not
        # rely on knowing every secret variable an operator may define.
        environment = {name: value for name, value in os.environ.items()
                       if name in _SCANNER_ENV_NAMES}
        try:
            returncode = run_engine_command([*command, str(temporary)],
                                            environment=environment,
                                            cwd=temporary.parent,
                                            timeout_seconds=timeout_seconds)
        except subprocess.TimeoutExpired:
            raise UploadScanError("upload scanner exceeded its time limit") from None
        if returncode != 0:
            raise UploadScanError("upload rejected by virus scanner")
    except OSError:
        raise UploadScanError("upload scanner could not be executed") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
