"""Bounded subprocess boundary for operator-provided local OCR engines."""
from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from app.process_sandbox import (
    isolated_process_options,
    sandbox_environment,
    terminate_process_group,
)


class OcrError(ValueError):
    """Raised when an OCR adapter is unavailable or returns an invalid result."""


_MAX_STDOUT_BYTES = 4_000_000
_MAX_ELEMENTS_PER_PAGE = 10_000


def _run_bounded(command: list[str], temporary: Path, language: str,
                 environment: dict[str, str], directory: str,
                 timeout_seconds: int) -> tuple[int, bytes]:
    """Stream OCR stdout and terminate the child when the byte limit is exceeded."""
    process = subprocess.Popen([*command, str(temporary), language], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               env=environment, cwd=directory, **isolated_process_options())
    chunks: Queue[bytes] = Queue()

    def drain() -> None:
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(64 * 1024)
            chunks.put(chunk)
            if not chunk:
                return

    reader = threading.Thread(target=drain, name="docplatform-ocr-stdout", daemon=True)
    reader.start()
    output = bytearray()
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            terminate_process_group(process)
            process.wait()
            reader.join(timeout=1)
            raise subprocess.TimeoutExpired(process.args, timeout_seconds)
        try:
            chunk = chunks.get(timeout=min(0.05, remaining))
        except Empty:
            continue
        if not chunk:
            break
        output.extend(chunk)
        if len(output) > _MAX_STDOUT_BYTES:
            terminate_process_group(process)
            process.wait()
            reader.join(timeout=1)
            raise OcrError("OCR output exceeds the configured limit")
    reader.join(timeout=max(0.0, deadline - time.monotonic()))
    returncode = process.wait(timeout=max(0.01, deadline - time.monotonic()))
    return returncode, bytes(output)


def _validate_box(box: Any, context: str) -> list[float]:
    if not isinstance(box, list) or len(box) != 4:
        raise OcrError(f"OCR returned an invalid box for {context}")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in box):
        raise OcrError(f"OCR returned an invalid box for {context}")
    normalized = [float(value) for value in box]
    if any(value < 0 for value in normalized) or normalized[2] <= normalized[0] or normalized[3] <= normalized[1]:
        raise OcrError(f"OCR returned an invalid box for {context}")
    return normalized


def _validate_pages(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("pages"), list):
        raise OcrError("OCR output must be an object with a pages array")
    if not payload["pages"]:
        raise OcrError("OCR output must contain at least one page")
    pages: list[dict[str, Any]] = []
    seen_pages: set[int] = set()
    for page in payload["pages"]:
        if not isinstance(page, dict) or isinstance(page.get("page_number"), bool) or not isinstance(page.get("page_number"), int):
            raise OcrError("OCR returned an invalid page number")
        page_number = page["page_number"]
        if page_number < 1 or page_number in seen_pages:
            raise OcrError("OCR returned duplicate or invalid page numbers")
        seen_pages.add(page_number)
        elements = page.get("elements", [])
        if not isinstance(elements, list) or len(elements) > _MAX_ELEMENTS_PER_PAGE:
            raise OcrError("OCR returned too many page elements")
        checked: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, element in enumerate(elements):
            if not isinstance(element, dict) or not isinstance(element.get("text"), str):
                raise OcrError(f"OCR returned an invalid text element on page {page_number}")
            text = element["text"]
            if not text or len(text) > 100_000:
                raise OcrError(f"OCR returned an invalid text value on page {page_number}")
            element_id = str(element.get("id") or f"ocr-{page_number}-{index + 1}")
            if len(element_id) > 160 or element_id in seen_ids:
                raise OcrError(f"OCR returned a duplicate or overlong element ID on page {page_number}")
            seen_ids.add(element_id)
            item = {"id": element_id,
                    "type": "text", "text": text,
                    "box": _validate_box(element.get("box"), f"page {page_number}")}
            confidence = element.get("confidence")
            if confidence is not None:
                if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                    raise OcrError(f"OCR returned an invalid confidence on page {page_number}")
                item["confidence"] = float(confidence)
            checked.append(item)
        pages.append({"page_number": page_number, "elements": checked})
    return pages


def run_ocr(data: bytes, command: list[str], language: str, timeout_seconds: int) -> dict[str, Any]:
    """Run ``command input.upload language`` and parse its JSON stdout.

    The adapter is deliberately engine-neutral. A PaddleOCR or Tesseract wrapper
    can implement the protocol without adding an unreviewed model dependency to
    the core image. The child receives no application credentials and cannot use
    a shell through this boundary.
    """
    if not command:
        raise OcrError("configured OCR engine is not installed")
    if not all(isinstance(part, str) and part for part in command):
        raise OcrError("OCR command configuration is invalid")
    try:
        with tempfile.TemporaryDirectory(prefix="docplatform-ocr-") as directory:
            temporary = Path(directory) / "input.upload"
            temporary.write_bytes(data)
            environment = sandbox_environment(directory)
            try:
                returncode, stdout = _run_bounded(command, temporary, language, environment,
                                                  directory, timeout_seconds)
            except subprocess.TimeoutExpired:
                raise OcrError("OCR engine exceeded its time limit") from None
            if returncode != 0:
                raise OcrError("OCR engine returned a failure")
            try:
                payload = json.loads(stdout.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise OcrError("OCR output is not valid UTF-8 JSON") from None
            return {"pages": _validate_pages(payload)}
    except OSError:
        raise OcrError("OCR engine could not be executed") from None
