"""Offline SVG generators for declarative QR and 1-D code blocks."""
from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import barcode
import qrcode
from barcode.writer import SVGWriter
from qrcode.image.svg import SvgPathImage

from app.security import validate_svg_markup


def _validated_svg(markup: str) -> str:
    """Validate library output before embedding generated markup in a document."""
    # python-barcode emits an XML declaration and a public SVG 1.1 DOCTYPE.
    # The latter references an external DTD and is unnecessary for an embedded
    # SVG, so remove only this generated prolog before applying the strict gate.
    markup = re.sub(r"<\?xml[^>]*>\s*", "", markup, count=1, flags=re.IGNORECASE)
    markup = re.sub(r"<!DOCTYPE\s+svg(?:.|\r|\n)*?>\s*", "", markup, count=1, flags=re.IGNORECASE)
    try:
        validate_svg_markup(markup.encode("utf-8"))
    except ValueError as error:
        raise ValueError("generated code SVG failed safety validation") from error
    if not re.search(r"<(?:path|rect|line|polygon|polyline)\b", markup, re.IGNORECASE):
        raise ValueError("generated code SVG contains no drawable geometry")
    return markup


def _validate_ean13(text: str) -> None:
    if not re.fullmatch(r"\d{12,13}", text):
        raise ValueError("EAN-13 values must contain 12 or 13 digits")
    digits = text[:12]
    expected = (10 - (sum(int(digit) * (1 if index % 2 == 0 else 3)
                          for index, digit in enumerate(digits)) % 10)) % 10
    if len(text) == 13 and int(text[-1]) != expected:
        raise ValueError("EAN-13 check digit is invalid")


def render_code(kind: str, value: Any) -> str:
    text = str(value)
    if not text or len(text) > 200:
        raise ValueError("code value must contain between 1 and 200 characters")
    if kind == "qr":
        code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=4)
        code.add_data(text)
        code.make(fit=True)
        return _validated_svg(code.make_image(image_factory=SvgPathImage).to_string().decode("utf-8"))
    if kind not in {"code128", "ean13"}:
        raise ValueError("code.type must be qr, code128, or ean13")
    if kind == "ean13":
        _validate_ean13(text)
    generator = barcode.get_barcode_class(kind)(text, writer=SVGWriter())
    buffer = generator.render({"write_text": False, "quiet_zone": 2.5})
    if isinstance(buffer, BytesIO):
        buffer = buffer.getvalue()
    return _validated_svg(bytes(buffer).decode("utf-8"))
