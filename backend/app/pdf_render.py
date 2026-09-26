"""Shell-free boundary for an operator-provided designer HTML-to-PDF engine."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.process_sandbox import run_engine_command, sandbox_environment
from app.renderer_adapter import RendererAdapterError, build_command
from app.security import validate_pdf_active_content
from app.word_convert import WordConversionError, patch_pdf_metadata


class PdfRenderError(RuntimeError):
    pass


class PdfRenderUnavailable(PdfRenderError):
    pass


def render_html_to_pdf(html: str, command: list[str], timeout_seconds: int,
                       max_output_bytes: int, metadata: dict[str, str],
                       renderer: str = "chromium", license_file: Path | None = None) -> tuple[bytes, dict[str, object]]:
    """Run ``command input.html output.pdf`` and validate the candidate PDF."""
    if not command:
        raise PdfRenderUnavailable(f"designer PDF renderer '{renderer}' is not configured")
    if not isinstance(html, str) or not html:
        raise PdfRenderError("rendered HTML is empty")
    html_bytes = html.encode("utf-8")
    if len(html_bytes) > max_output_bytes:
        raise PdfRenderError("rendered HTML exceeds the configured size limit")
    try:
        with tempfile.TemporaryDirectory(prefix="docplatform-pdf-") as directory:
            root = Path(directory)
            source = root / "input.html"
            target = root / "output.pdf"
            source.write_bytes(html_bytes)
            environment = sandbox_environment(directory)
            try:
                try:
                    engine_command = build_command(renderer, command, source, target, license_file)
                except RendererAdapterError as exc:
                    raise PdfRenderError(str(exc)) from None
                returncode = run_engine_command(engine_command,
                                                environment=environment, cwd=directory,
                                                timeout_seconds=timeout_seconds)
            except subprocess.TimeoutExpired:
                raise PdfRenderError("designer PDF renderer exceeded its time limit") from None
            if returncode != 0:
                detail = "designer PDF renderer returned a failure"
                stderr_path = root / "engine.stderr"
                if stderr_path.is_file():
                    message = stderr_path.read_text(encoding="utf-8", errors="replace").strip()
                    if message:
                        detail = f"{detail}: {message[-500:]}"
                raise PdfRenderError(detail)
            if not target.is_file():
                raise PdfRenderError("designer PDF renderer did not produce a PDF")
            output = target.read_bytes()
    except OSError:
        raise PdfRenderError("designer PDF renderer could not be executed") from None
    if len(output) > max_output_bytes:
        raise PdfRenderError("generated PDF exceeds the configured size limit")
    if not output.startswith(b"%PDF-"):
        raise PdfRenderError("designer PDF renderer returned an invalid PDF")
    try:
        output = patch_pdf_metadata(output, metadata)
    except (TypeError, ValueError, WordConversionError) as exc:
        raise PdfRenderError(f"generated PDF metadata could not be patched: {exc}") from None
    if len(output) > max_output_bytes:
        raise PdfRenderError("generated PDF with metadata exceeds the configured size limit")
    try:
        validate_pdf_active_content(output)
    except ValueError as exc:
        raise PdfRenderError(str(exc)) from None
    return output, {"engine": renderer, "status": "candidate",
                    "output_bytes": len(output), "metadata": metadata,
                    "license_configured": license_file is not None,
                    "native_reader_review": "pending", "fidelity": "pending"}
