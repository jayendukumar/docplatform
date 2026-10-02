"""Offline SourceModel analysis of digital PDFs (E16-02).

A small content-stream interpreter tracks the PDF graphics and text state
(CTM, Tm/Tlm, Tf, Tc, Tw, Tz, TL, Ts, Tr) and computes every glyph origin from
the font's width metrics. pypdf is used only to parse content streams and to
decode character codes and widths (``pypdf._cmap``, pinned to pypdf 6.1.3).

pypdf's own text extraction is deliberately not used for geometry: in 6.1.3 it
scales ``T*`` leading by the font size twice, does not advance the text
position after ``Tj``, and merges separately positioned text on one baseline.

Coordinates are millimetres from the page's top-left corner; text ``y_mm`` is
the baseline. Words are split at whitespace, at glyph gaps wider than
``WORD_GAP_EM``, and at font or font-size changes. Lines split at gaps wider
than ``LINE_GAP_EM``; gaps wider than ``TAB_GAP_EM`` inside a line are written
as ``	`` in the line text and recorded in ``tabs_mm``. Text outside the page box is kept and flagged ``off_page``;
invisible text (rendering mode 3, e.g. OCR layers) is flagged ``invisible``.
"""
from __future__ import annotations

import hashlib
import itertools
import math
import re
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf._cmap import build_char_map_from_dict, build_font_width_map
from pypdf.generic import ContentStream, IndirectObject

SOURCE_MODEL_VERSION = "source-model-v2"
PT_TO_MM = 25.4 / 72
MAX_PAGES = 500
MAX_GLYPHS_PER_PAGE = 200_000
MAX_GRAPHICS_PER_PAGE = 20_000
MAX_FORM_DEPTH = 8
RULE_THICKNESS_PT = 2.0
WORD_GAP_EM = 0.2
LINE_GAP_EM = 2.5
TAB_GAP_EM = 1.0

_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_BOLD = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
_ITALIC = re.compile(r"italic|oblique", re.IGNORECASE)
_IDENTITY = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


class SourceModelError(ValueError):
    """Raised when a PDF cannot be analysed within the harness bounds."""


def _mult(m: list[float], n: list[float]) -> list[float]:
    return [m[0] * n[0] + m[1] * n[2], m[0] * n[1] + m[1] * n[3],
            m[2] * n[0] + m[3] * n[2], m[2] * n[1] + m[3] * n[3],
            m[4] * n[0] + m[5] * n[2] + n[4], m[4] * n[1] + m[5] * n[3] + n[5]]


def _apply(m: list[float], x: float, y: float) -> tuple[float, float]:
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def _resolve(value: Any) -> Any:
    return value.get_object() if isinstance(value, IndirectObject) else value


def _num(value: Any) -> float:
    return float(_resolve(value))


def font_traits(base_font: str) -> dict[str, Any]:
    """Classify a PDF base-font name into family class, weight and style."""
    name = _SUBSET_PREFIX.sub("", base_font.lstrip("/"))
    lowered = name.lower()
    if "sans" in lowered or any(key in lowered for key in ("arial", "helvetica", "verdana", "calibri", "segoe")):
        family_class = "sans"
    elif any(key in lowered for key in ("mono", "courier", "consol")):
        family_class = "mono"
    elif any(key in lowered for key in ("times", "serif", "georgia", "garamond", "cambria", "roman", "book")):
        family_class = "serif"
    else:
        family_class = "unknown"
    return {"font": name, "family_class": family_class,
            "bold": bool(_BOLD.search(name)), "italic": bool(_ITALIC.search(name))}


class _Font:
    """Decoding and width metrics for one font dictionary."""

    def __init__(self, font: Any) -> None:
        _, _, self.encoding, self.unicode_map = build_char_map_from_dict(200.0, font)
        self.bytes_per_code = 2 if self.unicode_map.get(-1) == 2 else 1
        self.widths = build_font_width_map(font, 0.0)
        self.has_widths = "/Widths" in font or "/DescendantFonts" in font
        self.traits = font_traits(str(font.get("/BaseFont", "")))
        matrix = _resolve(font.get("/FontMatrix")) if font.get("/Subtype") == "/Type3" else None
        self.unit = _num(matrix[0]) if matrix else 0.001

    def glyphs(self, data: bytes) -> list[tuple[str, float, bool]]:
        """Return (unicode, width in glyph space, is single-byte space) per character code."""
        result = []
        step = self.bytes_per_code
        for index in range(0, len(data) - step + 1, step):
            code_bytes = data[index:index + step]
            code = int.from_bytes(code_bytes, "big")
            if isinstance(self.encoding, str):
                try:
                    decoded = code_bytes.decode(self.encoding, "surrogatepass")
                except (UnicodeDecodeError, LookupError):
                    decoded = chr(code)
            else:
                decoded = self.encoding.get(code, chr(code)) if step == 1 else chr(code)
            text = self.unicode_map.get(decoded, decoded)
            width = self.widths.get(chr(code), self.widths.get("default", 0.0)) or 0.0
            result.append((text if isinstance(text, str) else str(text), float(width), step == 1 and code == 32))
        return result


def _fill_hex(operator: bytes, operands: list[Any]) -> str:
    """Approximate a non-stroking colour as #RRGGBB (gray, RGB, CMYK; patterns fall back to black)."""
    try:
        values = [max(0.0, min(1.0, _num(v))) for v in operands if not isinstance(_resolve(v), str)]
    except (TypeError, ValueError):
        return "#000000"
    if operator == b"k" or len(values) == 4:
        c, m, y, k = (values + [0, 0, 0, 0])[:4]
        rgb = [(1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)]
    elif len(values) >= 3:
        rgb = values[:3]
    elif values:
        rgb = [values[0]] * 3
    else:
        return "#000000"
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgb)


def _classify_rect(x0: float, y0: float, x1: float, y1: float, filled: bool) -> str:
    if min(abs(x1 - x0), abs(y1 - y0)) <= RULE_THICKNESS_PT:
        return "rule"
    return "filled-box" if filled else "box"


class _PageInterpreter:
    def __init__(self, page: Any, index: int) -> None:
        box = page.mediabox
        self.left, self.bottom = float(box.left), float(box.bottom)
        self.width_pt, self.height_pt = float(box.width), float(box.height)
        self.page = page
        self.index = index
        self.glyphs: list[dict[str, Any]] = []
        self.graphics: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.font_cache: dict[int, _Font] = {}

    def to_mm(self, x: float, y: float) -> tuple[float, float]:
        return (round((x - self.left) * PT_TO_MM, 3),
                round((self.height_pt - (y - self.bottom)) * PT_TO_MM, 3))

    def _font(self, resources: Any, name: Any) -> _Font | None:
        fonts = _resolve(resources.get("/Font")) if resources else None
        font = _resolve(fonts.get(name)) if fonts else None
        if font is None:
            return None
        key = id(font)
        if key not in self.font_cache:
            self.font_cache[key] = _Font(font)
        return self.font_cache[key]

    def run(self) -> None:
        if self.page.get_contents() is None:
            return
        self._interpret(ContentStream(self.page.get_contents(), self.page.pdf),
                        _resolve(self.page.get("/Resources")) or {}, list(_IDENTITY), 0)

    def _interpret(self, stream: ContentStream, resources: Any, ctm: list[float], depth: int) -> None:
        stack: list[tuple[list[float], dict[str, Any]]] = []
        # Text state plus the non-stroking (fill) colour; both are part of the graphics state saved by q/Q.
        text: dict[str, Any] = {"font": None, "size": 0.0, "Tc": 0.0, "Tw": 0.0, "Th": 1.0, "TL": 0.0, "Ts": 0.0, "Tr": 0,
                                "fill": "#000000", "stroke": "#000000", "line_width": 1.0}
        tm = list(_IDENTITY)
        tlm = list(_IDENTITY)
        path: list[tuple[str, list[tuple[float, float]]]] = []

        def show(data: Any) -> None:
            font: _Font | None = text["font"]
            if font is None or not isinstance(data, (bytes, str)):
                return
            raw = getattr(data, "original_bytes", None) or (data if isinstance(data, bytes)
                                                              else data.encode("latin-1", "replace"))
            size, th = text["size"], text["Th"]
            for char, width, is_space in font.glyphs(raw):
                if len(self.glyphs) >= MAX_GLYPHS_PER_PAGE:
                    raise SourceModelError(f"page {self.index + 1} exceeds {MAX_GLYPHS_PER_PAGE} glyphs")
                user = _mult(tm, ctm)
                trm = _mult([size * th, 0, 0, size, 0, text["Ts"]], user)
                advance = (width * font.unit * size + text["Tc"] + (text["Tw"] if is_space else 0.0)) * th
                self.glyphs.append({"char": char, "origin": (trm[4], trm[5]),
                                    "advance": advance * math.hypot(user[0], user[1]),
                                    "size": abs(size) * math.hypot(user[2], user[3]),
                                    "rotated": abs(trm[1]) > 1e-3 or abs(trm[2]) > 1e-3,
                                    "font": font, "invisible": text["Tr"] in (3, 7)})
                tm[:] = _mult([1, 0, 0, 1, advance, 0], tm)

        def next_line() -> None:
            tlm[:] = _mult([1, 0, 0, 1, 0, -text["TL"]], tlm)
            tm[:] = list(tlm)

        def add_graphic(kind: str, points: list[tuple[float, float]], filled: bool) -> None:
            if len(self.graphics) >= MAX_GRAPHICS_PER_PAGE:
                raise SourceModelError(f"page {self.index + 1} exceeds {MAX_GRAPHICS_PER_PAGE} graphics")
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            if kind == "rect":
                kind = _classify_rect(x0, y0, x1, y1, filled)
            (ax, ay), (bx, by) = self.to_mm(x0, y1), self.to_mm(x1, y0)
            # Thickness: the thin side of a filled rule, or the scaled stroke width of a stroked path.
            stroke_pt = text["line_width"] * math.hypot(ctm[0], ctm[1])
            thickness = min(abs(x1 - x0), abs(y1 - y0)) if filled else stroke_pt
            self.graphics.append({"kind": kind, "box_mm": [ax, ay, bx, by], "filled": filled,
                                  "fill": text["fill"] if filled else None,
                                  "stroke": None if filled else text["stroke"],
                                  "thickness_pt": round(thickness, 3)})

        def add_image(matrix: list[float]) -> None:
            corners = [_apply(matrix, x, y) for x, y in ((0, 0), (1, 0), (1, 1), (0, 1))]
            xs, ys = [p[0] for p in corners], [p[1] for p in corners]
            (ax, ay), (bx, by) = self.to_mm(min(xs), max(ys)), self.to_mm(max(xs), min(ys))
            self.images.append({"box_mm": [ax, ay, bx, by]})

        for operands, operator in stream.operations:
            if operator == b"q":
                stack.append((list(ctm), dict(text)))
            elif operator == b"Q" and stack:
                ctm, text = stack.pop()
            elif operator == b"cm" and len(operands) == 6:
                ctm = _mult([_num(v) for v in operands], ctm)
            elif operator == b"BT":
                tm[:], tlm[:] = list(_IDENTITY), list(_IDENTITY)
            elif operator == b"Tf" and len(operands) == 2:
                text["font"] = self._font(resources, operands[0])
                text["size"] = _num(operands[1])
            elif operator in {b"Tc", b"Tw", b"TL", b"Ts"} and operands:
                text[operator.decode()] = _num(operands[0])
            elif operator == b"Tz" and operands:
                text["Th"] = _num(operands[0]) / 100
            elif operator in {b"g", b"rg", b"k", b"sc", b"scn"} and operands:
                text["fill"] = _fill_hex(operator, operands)
            elif operator in {b"G", b"RG", b"K", b"SC", b"SCN"} and operands:
                text["stroke"] = _fill_hex(operator.lower(), operands)
            elif operator == b"w" and operands:
                text["line_width"] = _num(operands[0])
            elif operator == b"Tr" and operands:
                text["Tr"] = int(_num(operands[0]))
            elif operator in {b"Td", b"TD"} and len(operands) == 2:
                tx, ty = _num(operands[0]), _num(operands[1])
                if operator == b"TD":
                    text["TL"] = -ty
                tlm[:] = _mult([1, 0, 0, 1, tx, ty], tlm)
                tm[:] = list(tlm)
            elif operator == b"Tm" and len(operands) == 6:
                tlm[:] = [_num(v) for v in operands]
                tm[:] = list(tlm)
            elif operator == b"T*":
                next_line()
            elif operator == b"Tj" and operands:
                show(operands[0])
            elif operator == b"'" and operands:
                next_line()
                show(operands[0])
            elif operator == b'"' and len(operands) == 3:
                text["Tw"], text["Tc"] = _num(operands[0]), _num(operands[1])
                next_line()
                show(operands[2])
            elif operator == b"TJ" and operands:
                for item in operands[0]:
                    if isinstance(item, (bytes, str)):
                        show(item)
                    else:
                        tm[:] = _mult([1, 0, 0, 1, -_num(item) / 1000 * text["size"] * text["Th"], 0], tm)
            elif operator == b"re" and len(operands) == 4:
                x, y, w, h = (_num(v) for v in operands)
                path.append(("rect", [_apply(ctm, x, y), _apply(ctm, x + w, y),
                                      _apply(ctm, x + w, y + h), _apply(ctm, x, y + h)]))
            elif operator == b"m" and len(operands) == 2:
                path.append(("line", [_apply(ctm, _num(operands[0]), _num(operands[1]))]))
            elif operator == b"l" and len(operands) == 2 and path and path[-1][0] == "line":
                path[-1][1].append(_apply(ctm, _num(operands[0]), _num(operands[1])))
            elif operator in {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"}:
                filled = operator not in {b"S", b"s"}
                for kind, points in path:
                    if kind == "rect":
                        add_graphic("rect", points, filled)
                        continue
                    for start, end in itertools.pairwise(points):
                        straight = abs(start[1] - end[1]) < 0.5 or abs(start[0] - end[0]) < 0.5
                        add_graphic("rule" if straight else "segment", [start, end], False)
                path = []
            elif operator == b"n":
                path = []
            elif operator == b"INLINE IMAGE":
                add_image(ctm)
            elif operator == b"Do" and operands:
                xobjects = _resolve(resources.get("/XObject")) if resources else None
                xobject = _resolve(xobjects.get(operands[0])) if xobjects else None
                if xobject is None:
                    continue
                subtype = xobject.get("/Subtype")
                if subtype == "/Image":
                    add_image(ctm)
                elif subtype == "/Form" and depth < MAX_FORM_DEPTH:
                    matrix = [_num(v) for v in xobject.get("/Matrix", _IDENTITY)]
                    form_resources = _resolve(xobject.get("/Resources")) or resources
                    self._interpret(ContentStream(xobject, self.page.pdf), form_resources,
                                    _mult(matrix, ctm), depth + 1)

    def words(self) -> list[dict[str, Any]]:
        words: list[dict[str, Any]] = []
        current: list[dict[str, Any]] = []

        def flush() -> None:
            if not current:
                return
            first, last = current[0], current[-1]
            x_mm, y_mm = self.to_mm(*first["origin"])
            sizes = sorted(g["size"] for g in current)
            words.append({"text": "".join(g["char"] for g in current), "x_mm": x_mm, "y_mm": y_mm,
                          "width_mm": round((last["origin"][0] + last["advance"] - first["origin"][0]) * PT_TO_MM, 3),
                          "size_pt": round(sizes[len(sizes) // 2], 2), **first["font"].traits,
                          "width_source": "font-widths" if first["font"].has_widths else "font-default",
                          "rotated": first["rotated"], "invisible": first["invisible"],
                          "off_page": not (0 <= x_mm <= self.width_pt * PT_TO_MM
                                           and 0 <= y_mm <= self.height_pt * PT_TO_MM)})
            current.clear()

        for glyph in self.glyphs:
            if not glyph["char"].strip():
                flush()
                continue
            if current:
                previous = current[-1]
                gap = glyph["origin"][0] - (previous["origin"][0] + previous["advance"])
                if (abs(glyph["origin"][1] - previous["origin"][1]) > 0.3 * previous["size"]
                        or abs(gap) > WORD_GAP_EM * previous["size"]
                        or abs(glyph["size"] - previous["size"]) > 0.2 * previous["size"]
                        or glyph["font"] is not previous["font"] or glyph["invisible"] != previous["invisible"]):
                    flush()
            current.append(glyph)
        flush()
        return words

    def model(self) -> dict[str, Any]:
        words = self.words()
        width_mm = round(self.width_pt * PT_TO_MM, 3)
        gutter = find_gutter(words, width_mm)
        for word in words:
            word["column"] = 1 if gutter is not None and word["x_mm"] >= gutter else 0
        return {"page_number": self.index + 1,
                "width_mm": width_mm, "height_mm": round(self.height_pt * PT_TO_MM, 3),
                "gutter_mm": gutter, "words": words, "lines": group_lines(words, gutter),
                "graphics": self.graphics, "images": self.images}


def find_gutter(words: list[dict[str, Any]], width_mm: float) -> float | None:
    """Return the x of a two-column gutter, or None.

    A gutter is a vertical whitespace band in the middle 30-70% of the page that at most 10% of rows cross,
    with prose (at least four words each side) in at least 30% of rows. The prose test keeps tables,
    whose cells are short, from being read as columns.
    """
    rows: dict[float, list[dict[str, Any]]] = {}
    for word in words:
        if not (word["rotated"] or word["off_page"] or word["invisible"]):
            rows.setdefault(round(word["y_mm"] * 2) / 2, []).append(word)
    if len(rows) < 12:
        return None
    low, high = int(width_mm * 0.3), int(width_mm * 0.7)
    crossing = [0] * (high - low + 1)
    for row in rows.values():
        for word in row:
            for x in range(max(low, int(word["x_mm"])), min(high, int(word["x_mm"] + word["width_mm"])) + 1):
                crossing[x - low] += 1
    limit = 0.1 * len(rows)  # full-width titles, headers and footers may cross the gutter
    best: tuple[int, int] | None = None
    start = None
    for offset, count in enumerate([*crossing, limit + 1]):
        if count <= limit and start is None:
            start = offset
        elif count > limit and start is not None:
            if offset - start >= 3 and (best is None or offset - start > best[1] - best[0]):
                best = (start, offset)
            start = None
    if best is None:
        return None
    gutter = low + (best[0] + best[1]) / 2
    both = [row for row in rows.values()
            if sum(w["x_mm"] < gutter for w in row) >= 4 and sum(w["x_mm"] >= gutter for w in row) >= 4]
    return round(gutter, 1) if len(both) >= 0.3 * len(rows) else None


def group_lines(words: list[dict[str, Any]], gutter: float | None = None) -> list[dict[str, Any]]:
    """Group visible words sharing a baseline into lines, split at gaps wider than LINE_GAP_EM and at a gutter."""
    visible = sorted(({**w, "_index": i} for i, w in enumerate(words)
                      if not (w["rotated"] or w["off_page"] or w["invisible"])),
                     key=lambda w: (w["y_mm"], w["x_mm"]))
    rows: list[list[dict[str, Any]]] = []
    for word in visible:
        if rows and abs(rows[-1][0]["y_mm"] - word["y_mm"]) <= 0.35 * word["size_pt"] * PT_TO_MM:
            rows[-1].append(word)
        else:
            rows.append([word])
    lines: list[dict[str, Any]] = []
    for row in rows:
        row.sort(key=lambda w: w["x_mm"])
        segment = [row[0]]
        for word in row[1:]:
            previous = segment[-1]
            gap = word["x_mm"] - (previous["x_mm"] + previous["width_mm"])
            # Split at the gutter only where there is a real gap; full-width titles and footers run across it.
            crosses_gutter = (gutter is not None and previous["x_mm"] < gutter <= word["x_mm"]
                              and gap > TAB_GAP_EM * previous["size_pt"] * PT_TO_MM)
            if crosses_gutter or gap > LINE_GAP_EM * previous["size_pt"] * PT_TO_MM:
                lines.append(_line(segment))
                segment = [word]
            else:
                segment.append(word)
        lines.append(_line(segment))
    return lines


def _line(segment: list[dict[str, Any]]) -> dict[str, Any]:
    weights: Counter[str] = Counter()
    for word in segment:
        weights[word["font"]] += len(word["text"])
    dominant = next(w for w in segment if w["font"] == weights.most_common(1)[0][0])
    sizes = sorted(w["size_pt"] for w in segment)
    end = max(w["x_mm"] + w["width_mm"] for w in segment)
    # Join words with a space only where there is a visible gap (font changes split words without one),
    # with a tab where the gap exceeds TAB_GAP_EM (a tab-like gap inside one line, e.g. after a clause
    # label), and merge consecutive words of the same style into runs for rich-text reconstruction.
    text = ""
    runs: list[dict[str, Any]] = []
    tabs: list[float] = []
    previous = None
    for word in segment:
        separator = ""
        if previous is not None:
            gap = word["x_mm"] - (previous["x_mm"] + previous["width_mm"])
            em = previous["size_pt"] * PT_TO_MM
            separator = "\t" if gap > TAB_GAP_EM * em else " " if gap > 0.1 * em else ""
            if separator == "\t":
                tabs.append(word["x_mm"])
        style = (word["font"], word["bold"], word["italic"], word["size_pt"])
        if runs and runs[-1]["style"] == style:
            runs[-1]["text"] += separator + word["text"]
        else:
            if runs and separator:
                runs[-1]["text"] += separator
            runs.append({"style": style, "text": word["text"]})
        text += separator + word["text"]
        previous = word
    return {"text": text, "x_mm": segment[0]["x_mm"], "y_mm": segment[0]["y_mm"],
            "width_mm": round(end - segment[0]["x_mm"], 3), "size_pt": sizes[len(sizes) // 2],
            "font": dominant["font"], "family_class": dominant["family_class"],
            "bold": dominant["bold"], "italic": dominant["italic"], "words": len(segment),
            "word_indices": [w["_index"] for w in segment if "_index" in w], "tabs_mm": tabs,
            "column": segment[0].get("column", 0),
            "runs": [{"text": run["text"], "font": run["style"][0], "bold": run["style"][1],
                      "italic": run["style"][2], "size_pt": run["style"][3]} for run in runs]}


def analyse_pdf(data: bytes, *, label: str = "") -> dict[str, Any]:
    """Return a versioned SourceModel for a digital PDF."""
    try:
        pages = list(PdfReader(BytesIO(data)).pages)
    except Exception as exc:  # pypdf raises several unrelated exception types for malformed input
        raise SourceModelError(f"unreadable PDF: {exc}") from exc
    if len(pages) > MAX_PAGES:
        raise SourceModelError(f"PDF exceeds {MAX_PAGES} pages")
    analysed = []
    for index, page in enumerate(pages):
        interpreter = _PageInterpreter(page, index)
        interpreter.run()
        analysed.append(interpreter.model())
    all_words = [w for p in analysed for w in p["words"]]
    return {"contract": SOURCE_MODEL_VERSION, "label": label,
            "sha256": hashlib.sha256(data).hexdigest(), "page_count": len(analysed), "pages": analysed,
            "summary": {"words": len(all_words), "lines": sum(len(p["lines"]) for p in analysed),
                        "graphics": dict(Counter(g["kind"] for p in analysed for g in p["graphics"])),
                        "images": sum(len(p["images"]) for p in analysed),
                        "fonts": dict(Counter(w["font"] for w in all_words)),
                        "off_page_words": sum(w["off_page"] for w in all_words),
                        "invisible_words": sum(w["invisible"] for w in all_words),
                        "default_width_share": round(sum(w["width_source"] == "font-default" for w in all_words)
                                                     / max(1, len(all_words)), 4)}}


def analyse_path(path: Path) -> dict[str, Any]:
    return analyse_pdf(path.read_bytes(), label=path.name)
