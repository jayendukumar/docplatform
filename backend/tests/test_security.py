import sys
import zlib

import pytest

from app.security import (
    UploadScanError,
    scan_upload,
    validate_pdf_active_content,
    validate_svg_markup,
)


def test_optional_upload_scan_is_noop_when_unconfigured():
    scan_upload(b"safe", [], 1)


def test_upload_scan_accepts_clean_and_rejects_nonzero():
    clean = [sys.executable, "-c", "import sys; assert sys.argv[1] and open(sys.argv[1], 'rb').read() == b'safe'"]
    scan_upload(b"safe", clean, 2)
    infected = [sys.executable, "-c", "raise SystemExit(3)"]
    with pytest.raises(UploadScanError, match="rejected"):
        scan_upload(b"safe", infected, 2)


def test_upload_scan_discards_unbounded_scanner_output():
    noisy = [sys.executable, "-c", "import sys; sys.stdout.write('x' * 8_000_000); sys.stderr.write('y' * 8_000_000)"]
    scan_upload(b"safe", noisy, 2)


def test_upload_scan_does_not_inherit_arbitrary_application_secrets(monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_TEST_SECRET", "must-not-reach-scanner")
    command = [sys.executable, "-c",
               "import os,sys; raise SystemExit(0 if os.getenv('DOCPLATFORM_TEST_SECRET') else 3)"]
    with pytest.raises(UploadScanError, match="rejected"):
        scan_upload(b"safe", command, 2)


def test_upload_scan_times_out_and_cleans_up():
    slow = [sys.executable, "-c", "import time; time.sleep(5)"]
    with pytest.raises(UploadScanError, match="time limit"):
        scan_upload(b"safe", slow, 1)


def test_svg_markup_validation_rejects_active_content_and_accepts_safe_vector():
    with pytest.raises(ValueError, match="unsafe markup"):
        validate_svg_markup(b'<svg><script>alert(1)</script></svg>')
    validate_svg_markup(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1" /></svg>')


@pytest.mark.parametrize("token", [b"/JavaScript", b"/JS", b"/OpenAction", b"/EmbeddedFile", b"/XFA"])
def test_pdf_active_content_gate_rejects_common_action_tokens(token):
    with pytest.raises(ValueError, match="active content"):
        validate_pdf_active_content(b"%PDF-1.7\n<< " + token + b" 1 0 R >>")


def test_pdf_active_content_gate_scans_bounded_flate_streams():
    compressed = zlib.compress(b"<< /JavaScript 1 0 R >>")
    payload = (b"%PDF-1.7\n<< /Filter /FlateDecode >>\nstream\n" + compressed
               + b"\nendstream")
    with pytest.raises(ValueError, match="active content"):
        validate_pdf_active_content(payload)


@pytest.mark.parametrize("token", [b"/Java#53cript", b"/Open#41ction", b"/Emb#65ddedFile"])
def test_pdf_active_content_gate_rejects_hex_escaped_names(token):
    with pytest.raises(ValueError, match="active content"):
        validate_pdf_active_content(b"%PDF-1.7\n<< " + token + b" 1 0 R >>")
