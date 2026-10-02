"""Generate the project-authored E16 fidelity corpus (E16-01, DD-423).

Each document is typeset directly as PDF content streams with standard fonts,
independently of the Chromium renderer under test. Character widths are
measured once from PDFium's standard-font metrics (fidelity tooling, DD-419)
and embedded as ``/Widths`` so that layout, wrapping and justification are
exact and the analyser reads real glyph advances. All text is authored for
this project; the files are fixtures, not real agreements or records.

Usage: python scripts/build_fidelity_corpus.py [--out fidelity-corpus/generated]
"""
from __future__ import annotations

import argparse
import ctypes
import itertools
import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_VERSION = "fidelity-corpus-generator-v1"
FONTS = {"F1": "Helvetica", "F2": "Helvetica-Bold", "F3": "Times-Roman", "F4": "Times-Bold",
         "F5": "Times-Italic", "F6": "Courier"}
FIRST, LAST = 32, 126


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def measure_widths() -> dict[str, list[int]]:
    """Measure standard-font advance widths (glyph units) for ASCII 32-126 with PDFium."""
    import pypdfium2 as pdfium
    from pypdfium2 import raw

    chars = "".join(chr(c) for c in range(FIRST, LAST + 1))
    widths: dict[str, list[int]] = {}
    for key, base in FONTS.items():
        pdf = _document([f"BT /{key} 1000 Tf 0 100 Td ({_escape(chars)}X) Tj ET"], {}, {key: base})
        document = pdfium.PdfDocument(pdf)
        page = document[0]
        textpage = page.get_textpage()
        origins = []
        x, y = ctypes.c_double(), ctypes.c_double()
        for index in range(raw.FPDFText_CountChars(textpage.raw)):
            raw.FPDFText_GetCharOrigin(textpage.raw, index, ctypes.byref(x), ctypes.byref(y))
            origins.append(x.value)
        widths[key] = [round(b - a) for a, b in itertools.pairwise(origins)][: LAST - FIRST + 1]
        textpage.close()
        page.close()
        document.close()
        if len(widths[key]) != LAST - FIRST + 1:
            raise RuntimeError(f"could not measure {base}")
    return widths


def _document(pages: list[str], widths: dict[str, list[int]], fonts: dict[str, str] | None = None,
              title: str = "") -> bytes:
    writer = PdfWriter()
    font_dicts = DictionaryObject()
    for key, base in (fonts or FONTS).items():
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject(f"/{base}")})
        if key in widths:
            font[NameObject("/FirstChar")] = NumberObject(FIRST)
            font[NameObject("/LastChar")] = NumberObject(LAST)
            font[NameObject("/Widths")] = ArrayObject(NumberObject(w) for w in widths[key])
        font_dicts[NameObject(f"/{key}")] = writer._add_object(font)
    for content in pages:
        page = writer.add_blank_page(612, 792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): font_dicts})
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if title:
        writer.add_metadata({"/Title": TextStringObject(title), "/Producer": TextStringObject(GENERATOR_VERSION)})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class Page:
    """A Letter page with top-left coordinates in points."""

    def __init__(self, widths: dict[str, list[int]]) -> None:
        self.widths = widths
        self.ops: list[str] = []

    def width(self, text: str, font: str, size: float) -> float:
        table = self.widths[font]
        return sum(table[ord(c) - FIRST] if FIRST <= ord(c) <= LAST else table[0] for c in text) * size / 1000

    def text(self, x: float, y: float, text: str, font: str = "F3", size: float = 10, word_spacing: float = 0) -> None:
        self.ops.append(f"BT /{font} {size:g} Tf {word_spacing:.3f} Tw 1 0 0 1 {x:.2f} {792 - y:.2f} Tm "
                        f"({_escape(text)}) Tj ET")

    def aligned(self, x: float, right: float, y: float, text: str, align: str, font: str = "F3", size: float = 10) -> None:
        width = self.width(text, font, size)
        start = {"left": x, "right": right - width, "center": (x + right - width) / 2}[align]
        self.text(start, y, text, font, size)

    def paragraph(self, x: float, right: float, y: float, text: str, *, font: str = "F3", size: float = 10,
                  leading: float = 12, align: str = "left", first_indent: float = 0, hanging: float = 0) -> float:
        """Wrap and set a paragraph; returns the baseline after the last line."""
        words, lines, current = text.split(), [], []
        for word in words:
            indent = first_indent if not lines else hanging
            trial = " ".join([*current, word])
            if current and self.width(trial, font, size) > right - x - indent:
                lines.append(current)
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(current)
        for index, line in enumerate(lines):
            indent = first_indent if index == 0 else hanging
            line_text = " ".join(line)
            last = index == len(lines) - 1
            if align == "justify" and not last and len(line) > 1:
                slack = right - x - indent - self.width(line_text, font, size)
                self.text(x + indent, y, line_text, font, size, word_spacing=slack / (len(line) - 1))
            else:
                self.aligned(x + indent, right, y, line_text, "left" if align == "justify" else align, font, size)
            y += leading
        return y

    def rule(self, x1: float, x2: float, y: float, weight: float = 0.75) -> None:
        self.ops.append(f"{x1:.2f} {792 - y - weight / 2:.2f} {x2 - x1:.2f} {weight:.2f} re f")

    def box(self, x: float, y: float, w: float, h: float, *, fill: float | None = None) -> None:
        if fill is None:
            self.ops.append(f"0.75 w {x:.2f} {792 - y - h:.2f} {w:.2f} {h:.2f} re S")
        else:
            self.ops.append(f"{fill:.2f} g {x:.2f} {792 - y - h:.2f} {w:.2f} {h:.2f} re f 0 g")

    def content(self) -> str:
        return "\n".join(self.ops)


LOREM = ("This document is a project-authored fixture used to measure how faithfully the template editor can "
         "reproduce typical business layouts. Its wording is neutral and carries no legal or commercial meaning. "
         "Paragraphs are wrapped with measured font metrics so that line breaks, alignment and spacing are exact.")


def letter(widths: dict[str, list[int]]) -> list[str]:
    page = Page(widths)
    page.aligned(72, 540, 60, "NORTHWIND FIXTURE SERVICES", "center", "F2", 16)
    page.aligned(72, 540, 76, "12 Example Street, Sampletown, ST 00000", "center", "F1", 9)
    page.rule(72, 540, 86)
    page.aligned(72, 540, 120, "1 October 2026", "right", "F3", 11)
    for offset, line in enumerate(["Ms Avery Reader", "Accounts Department", "Placeholder Holdings", "99 Demo Road"]):
        page.text(72, 150 + offset * 13, line, "F3", 11)
    page.text(72, 220, "Subject: Annual service review", "F4", 11)
    y = page.paragraph(72, 540, 250, "Dear Ms Reader,", size=11, leading=14) + 6
    for index in range(3):
        y = page.paragraph(72, 540, y, LOREM, size=11, leading=14, align="justify" if index != 1 else "left",
                           first_indent=18 if index == 2 else 0) + 8
    y = page.paragraph(72, 540, y + 10, "Yours sincerely,", size=11, leading=14)
    page.rule(72, 250, y + 40, 0.5)
    page.text(72, y + 54, "Jordan Example, Service Manager", "F3", 11)
    return [page.content()]


def invoice(widths: dict[str, list[int]]) -> list[str]:
    page = Page(widths)
    page.text(72, 72, "INVOICE", "F2", 22)
    page.aligned(300, 540, 66, "Invoice no. INV-2026-0042", "right", "F1", 10)
    page.aligned(300, 540, 80, "Issue date 01/10/2026", "right", "F1", 10)
    page.text(72, 120, "Bill to", "F2", 10)
    for offset, line in enumerate(["Placeholder Holdings", "99 Demo Road", "Sampletown ST 00000"]):
        page.text(72, 134 + offset * 12, line, "F1", 10)
    columns = [(72, "Description", "left"), (330, "Qty", "right"), (420, "Unit price", "right"), (540, "Amount", "right")]
    page.box(72, 190, 468, 18, fill=0.85)
    for x, header, align in columns:
        if align == "left":
            page.text(x + 4, 203, header, "F2", 10)
        else:
            page.aligned(x - 90, x - 4, 203, header, "right", "F2", 10)
    rows = [("Template design workshop", "2", "450.00"), ("Rendering verification", "5", "120.00"),
            ("Extraction calibration set", "1", "980.00"), ("Support hours", "12", "75.00"),
            ("Accessibility review preparation", "3", "210.00")]
    y = 226
    total = 0.0
    for description, qty, price in rows:
        amount = int(qty) * float(price)
        total += amount
        page.text(76, y, description, "F1", 10)
        page.aligned(240, 326, y, qty, "right", "F1", 10)
        page.aligned(330, 416, y, price, "right", "F1", 10)
        page.aligned(420, 536, y, f"{amount:,.2f}", "right", "F1", 10)
        page.rule(72, 540, y + 6, 0.3)
        y += 20
    for label, value in (("Subtotal", total), ("Tax 10%", total * 0.1), ("Total due", total * 1.1)):
        y += 4
        page.aligned(330, 416, y, label, "right", "F2" if label == "Total due" else "F1", 10)
        page.aligned(420, 536, y, f"{value:,.2f}", "right", "F2" if label == "Total due" else "F1", 10)
        y += 14
    page.paragraph(72, 540, 720, "Payment terms: 30 days. This invoice is a project-authored fixture and requests "
                   "no payment.", font="F1", size=8, leading=10, align="center")
    return [page.content()]


def form(widths: dict[str, list[int]]) -> list[str]:
    page = Page(widths)
    page.aligned(72, 540, 64, "APPLICATION FORM (FIXTURE)", "center", "F2", 14)
    sections = [("Section A - Applicant details", ["Full name", "Date of birth", "Email address", "Telephone"]),
                ("Section B - Address", ["Street", "Town or city", "Postcode"]),
                ("Section C - Declaration", ["Signature", "Date"])]
    y = 100
    for heading, fields in sections:
        page.box(72, y, 468, 18, fill=0.88)
        page.text(78, y + 13, heading, "F2", 10)
        y += 36
        for field in fields:
            page.text(72, y, f"{field}:", "F1", 10)
            leader_start = 72 + page.width(f"{field}: ", "F1", 10)
            dots = "." * int((540 - leader_start) / page.width(".", "F1", 10))
            page.text(leader_start, y, dots, "F1", 10)
            y += 22
        y += 8
    page.text(72, y + 4, "Preferred contact:", "F1", 10)
    for offset, option in enumerate(["Email", "Telephone", "Post"]):
        x = 190 + offset * 100
        page.box(x, y - 5, 9, 9)
        page.text(x + 14, y + 4, option, "F1", 10)
    return [page.content()]


def report(widths: dict[str, list[int]]) -> list[str]:
    pages = []
    gutter, left, right, middle = 18, 72, 540, 306
    for number in range(1, 4):
        page = Page(widths)
        page.text(72, 40, "Quarterly Fixture Report", "F5", 9)
        page.aligned(72, 540, 40, "Internal - Fixture", "right", "F5", 9)
        page.rule(72, 540, 46, 0.5)
        y = 80
        if number == 1:
            page.aligned(72, 540, 90, "Template Platform Quarterly Report", "center", "F4", 18)
            y = 120
        for column, (x0, x1) in enumerate(((left, middle - gutter / 2), (middle + gutter / 2, right))):
            cy = y
            for section in range(2):
                page.text(x0, cy, f"{number}.{column * 2 + section + 1} Findings summary", "F4", 11)
                cy = page.paragraph(x0, x1, cy + 16, LOREM + " " + LOREM, size=9.5, leading=11.5, align="justify") + 10
        page.aligned(72, 540, 756, f"Page {number} of 3", "center", "F3", 9)
        pages.append(page.content())
    return pages


def statement(widths: dict[str, list[int]]) -> list[str]:
    pages = []
    rows = [(f"2026-09-{day:02d}", f"Fixture transaction reference {1000 + day}", (day * 37) % 500 + 0.25 * day)
            for day in range(1, 31)] * 2
    per_page = 28
    balance = 1000.0
    for page_index in range(0, len(rows), per_page):
        page = Page(widths)
        page.text(72, 64, "ACCOUNT STATEMENT (FIXTURE)", "F2", 13)
        page.aligned(300, 540, 64, "Account 00-000-0000", "right", "F1", 9)
        header_y = 100
        page.box(72, header_y - 13, 468, 18, fill=0.85)
        for x, label, align in ((76, "Date", "left"), (160, "Description", "left"), (460, "Amount", "right"),
                                (536, "Balance", "right")):
            if align == "left":
                page.text(x, header_y, label, "F2", 9)
            else:
                page.aligned(x - 80, x, header_y, label, "right", "F2", 9)
        y = header_y + 20
        for date, description, amount in rows[page_index:page_index + per_page]:
            balance += amount
            page.text(76, y, date, "F6", 9)
            page.text(160, y, description, "F1", 9)
            page.aligned(380, 460, y, f"{amount:,.2f}", "right", "F1", 9)
            page.aligned(456, 536, y, f"{balance:,.2f}", "right", "F1", 9)
            y += 21
        page.rule(72, 540, 740, 0.5)
        page.aligned(72, 540, 756, f"Statement page {page_index // per_page + 1}", "center", "F1", 8)
        pages.append(page.content())
    return pages


def contract(widths: dict[str, list[int]]) -> list[str]:
    pages = []
    clauses = [("1.", "Definitions", ["(a)", "(b)", "(c)"]), ("2.", "Obligations", ["(a)", "(b)"]),
               ("3.", "Term and termination", ["(a)", "(b)", "(c)"]), ("4.", "General", ["(a)", "(b)"])]
    page = Page(widths)
    page.aligned(72, 540, 70, "SERVICES AGREEMENT (FIXTURE)", "center", "F4", 15)
    y = page.paragraph(72, 540, 100, "This agreement is a project-authored fixture between Example Party A and "
                       "Example Party B and has no legal effect.", align="justify", size=10, leading=12.5) + 10
    for number, title, items in clauses:
        if y > 680:
            page.aligned(72, 540, 756, str(len(pages) + 1), "center", "F3", 9)
            pages.append(page.content())
            page = Page(widths)
            y = 80
        page.text(72, y, number, "F4", 10)
        page.text(108, y, title, "F4", 10)
        y += 16
        for item in items:
            page.text(108, y, item, "F3", 10)
            y = page.paragraph(144, 540, y, LOREM, align="justify", size=10, leading=12.5) + 6
            for roman in ("(i)", "(ii)") if item == "(a)" else ():
                page.text(144, y, roman, "F3", 10)
                y = page.paragraph(180, 540, y, "Sub-clause text wrapped with a hanging indent so that every line "
                                   "starts at the same position after the clause label.", align="justify",
                                   size=10, leading=12.5) + 4
        y += 8
    page.aligned(72, 540, 756, str(len(pages) + 1), "center", "F3", 9)
    pages.append(page.content())
    return pages


DOCUMENTS = {"letter": letter, "invoice": invoice, "form": form, "report": report, "statement": statement,
             "contract": contract}


def build(out: Path) -> dict[str, Path]:
    widths = measure_widths()
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, builder in DOCUMENTS.items():
        path = out / f"{name}.pdf"
        path.write_bytes(_document(builder(widths), widths, title=f"E16 fixture: {name}"))
        written[name] = path
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "fidelity-corpus" / "generated")
    args = parser.parse_args()
    for name, path in build(args.out).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
