import sys

import pytest

from app.ocr import OcrError, run_ocr


def _command(payload: dict) -> list[str]:
    return [sys.executable, "-c", f"import json,os,socket; assert os.path.basename(os.getcwd()).startswith('docplatform-ocr-'); assert socket.socket.connect.__module__ == 'sitecustomize'; assert 'DOCPLATFORM_DB_PASSWORD' not in os.environ; print(json.dumps({payload!r}))"]


def test_configured_local_ocr_returns_bounded_page_elements():
    result = run_ocr(b"image-bytes", _command({"pages": [{"page_number": 1, "elements": [
        {"id": "word-1", "text": "Invoice", "box": [1, 2, 30, 14], "confidence": 0.91},
    ]}]}), "eng", 2)
    assert result["pages"][0]["elements"][0]["box"] == [1.0, 2.0, 30.0, 14.0]
    assert result["pages"][0]["elements"][0]["confidence"] == 0.91


def test_ocr_is_unavailable_without_a_configured_command():
    with pytest.raises(OcrError, match="not installed"):
        run_ocr(b"image-bytes", [], "eng", 2)


def test_ocr_rejects_invalid_provenance():
    with pytest.raises(OcrError, match="invalid box"):
        run_ocr(b"image-bytes", _command({"pages": [{"page_number": 1, "elements": [
            {"text": "bad", "box": [1, 2, 2, 2]},
        ]}]}), "eng", 2)


def test_ocr_rejects_duplicate_element_ids():
    with pytest.raises(OcrError, match="duplicate"):
        run_ocr(b"image-bytes", _command({"pages": [{"page_number": 1, "elements": [
            {"id": "same", "text": "one", "box": [1, 2, 3, 4]},
            {"id": "same", "text": "two", "box": [5, 6, 7, 8]},
        ]}]}), "eng", 2)


def test_ocr_discards_unbounded_diagnostics_on_stderr():
    command = [sys.executable, "-c", (
        "import json,sys; sys.stderr.write('x' * (8 * 1024 * 1024)); "
        "print(json.dumps({'pages':[{'page_number':1,'elements':[]}]}))")]
    result = run_ocr(b"image-bytes", command, "eng", 2)
    assert result["pages"] == [{"page_number": 1, "elements": []}]


def test_ocr_terminates_when_stdout_exceeds_the_limit():
    command = [sys.executable, "-c", "import sys; sys.stdout.write('x' * 4000001); sys.stdout.flush()"]
    with pytest.raises(OcrError, match="output exceeds"):
        run_ocr(b"image-bytes", command, "eng", 2)
