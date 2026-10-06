"""E16 Phase B regression tests: taxonomy, reconstruction, validation and attribution (DD-421)."""
import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.capabilities import capability_manifest
from fidelity.attribute import attribute
from fidelity.compare import compare_models
from fidelity.reconstruct import reconstruct, validate_reconstruction
from fidelity.source_model import analyse_pdf
from fidelity.taxonomy import detect_features


def _font(name: str) -> DictionaryObject:
    return DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject(f"/{name}")})


def make_document(pages: list[str]) -> bytes:
    """Letter pages with /F1 Times-Roman and /F2 Times-Bold."""
    writer = PdfWriter()
    for content in pages:
        page = writer.add_blank_page(612, 792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject(
            {NameObject("/F1"): _font("Times-Roman"), NameObject("/F2"): _font("Times-Bold")})})
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def body_page(number: int) -> str:
    return (
        "BT /F2 14 Tf 250 720 Td (Agreement Title) Tj ET "
        "BT /F1 10 Tf 72 690 Td ((a)) Tj 36 0 Td (Definitions apply to this clause.) Tj ET "
        "BT /F1 10 Tf 72 670 Td (Plain body text that continues across one line only here.) Tj ET "
        "BT /F1 10 Tf 72 650 Td (Mixed ) Tj /F2 10 Tf (bold) Tj /F1 10 Tf ( style inside one paragraph.) Tj ET "
        "BT /F1 10 Tf 72 630 Td (Signed on ..................................) Tj ET "
        "72 600 468 0.5 re f "
        f"BT /F1 9 Tf 290 40 Td ({number}) Tj ET BT /F1 9 Tf 450 40 Td (Form 2002) Tj ET"
    )


def document() -> tuple[dict, dict]:
    model = analyse_pdf(make_document([body_page(n) for n in (1, 2, 3)]), label="synthetic.pdf")
    return model, detect_features(model)


def test_taxonomy_detects_structure_and_running_furniture():
    _, features = document()
    summary = features["summary"]
    assert features["contract"] == "fidelity-taxonomy-v1"
    for feature in ("page.running_footer", "page.page_number", "list.numbered_label", "tab.dot_leader",
                    "text.mixed_inline_style", "graphic.rule", "text.heading", "page.margins"):
        assert summary.get(feature), feature
    assert summary["page.running_footer"] == 3 and summary["page.page_number"] == 3
    label = next(d for d in features["detections"] if d["feature"] == "list.numbered_label")
    assert label["evidence"]["label"] == "(a)" and abs(label["evidence"]["gap_mm"] - 12.7) < 0.1
    furniture_lines = {tuple(ref) for refs in features["furniture"].values() for ref in refs}
    paragraph_lines = {tuple(ref) for paragraphs in features["paragraphs"].values() for p in paragraphs for ref in p["lines"]}
    assert furniture_lines and not furniture_lines & paragraph_lines


def test_reconstruction_is_editor_reachable_and_records_gaps():
    model, features = document()
    rebuilt = reconstruct(model, features)
    assert rebuilt["contract"] == "reconstruction-v1"
    assert validate_reconstruction(rebuilt, capability_manifest()) == []
    definition = rebuilt["definition"]
    assert definition["page"]["size"] == "Letter" and definition["page"]["show_page_numbers"] is True
    # DD-438: furniture maps to zones with a distance from the page edge.
    assert definition["page"]["footer_right"] == "Form 2002" and "footer" not in definition["page"]
    assert definition["page"]["page_number_position"] == "footer-center"
    assert 10 < definition["page"]["footer_distance_mm"] < 14
    assert "background_pdf" not in definition["page"]
    types = [block["type"] for block in definition["blocks"]]
    assert "rich_text" in types and "text" in types
    assert all(block["page_number"] in {1, 2, 3} for block in definition["blocks"])
    gaps = {(g["feature"], g["reason"], g["component"], g["property"]) for g in rebuilt["gaps"]}
    # DD-434: the 468 pt rule inside the content area becomes a positioned line shape, not a gap.
    assert not {g for g in gaps if g[0] == "graphic.rule"}
    (rule,) = [b for b in definition["blocks"] if b["type"] == "shape" and b["page_number"] == 1]
    assert rule["shape"] == "line" and rule["orientation"] == "horizontal" and rule["position_mode"] == "absolute"
    assert abs(rule["width_mm"] - 165.1) < 0.2 and rule["stroke_color"] == "#000000"
    # Since DD-424 to DD-427, clause labels and leaders are expressed with positioned tab stops.
    assert not {g for g in gaps if g[0] in {"list.numbered_label", "tab.positioned_gap", "tab.dot_leader"}}
    labelled = next(b for b in definition["blocks"] if b.get("type") == "text" and "Definitions" in b.get("text", ""))
    assert labelled["text"] == "(a)\tDefinitions apply to this clause." and labelled["tab_stops"] == [48.0]
    leader = next(b for b in definition["blocks"] if b.get("type") == "text" and b.get("text", "").startswith("Signed on"))
    assert leader["text"] == "Signed on\t"
    (stop,) = leader["tab_stops"]
    assert stop["align"] == "left" and stop["leader"] == "dot" and stop["position"] > 48
    mixed = next(b for b in definition["blocks"] if b["type"] == "rich_text")
    styles = [(run["text"].strip(), run["style"]["bold"]) for run in mixed["paragraphs"][0]["runs"]]
    assert ("bold", True) in styles
    assert len(rebuilt["provenance"]) == len(definition["blocks"])
    assert rebuilt["effort"]["blocks"] == len(definition["blocks"]) and rebuilt["effort"]["absolute_blocks"] == 0


def test_validator_rejects_unreachable_and_invalid_reconstructions():
    model, features = document()
    rebuilt = reconstruct(model, features)
    rebuilt["definition"]["page"]["background_pdf"] = {"asset": "x"}
    rebuilt["definition"]["blocks"][0]["translation_key"] = "k"      # renderer-only (ui=none)
    rebuilt["definition"]["blocks"][0]["font_size"] = 200            # outside 8-96
    rebuilt["definition"]["blocks"][0]["css"] = "position:fixed"     # not in the manifest
    rebuilt["gaps"].append({"feature": "text.paragraph", "reason": "looks-hard", "component": "text",
                            "property": "x", "detection_ids": []})
    violations = "\n".join(validate_reconstruction(rebuilt, capability_manifest()))
    assert "page.background_pdf: excluded from fidelity reconstruction" in violations
    assert "translation_key: not reachable from the editor" in violations
    assert "font_size: 200 outside [8, 96]" in violations
    assert "css: not a text property" in violations
    assert "unknown reason 'looks-hard'" in violations


def test_attribution_uses_alignment_evidence_and_flags_pagination():
    model, features = document()
    rebuilt = reconstruct(model, features)
    identical = compare_models(model, model, include_matches=True)
    clean = attribute(model, features, rebuilt, identical, None)
    assert clean["contract"] == "fidelity-attribution-v2" and clean["summary"]["global"] == []
    # The synthetic document is now fully expressible, so the evidence is checked on the control group.
    control = clean["summary"]["control_evidence"]
    # Leader "words" (dots only) carry no comparable text and are excluded from alignment, hence not 1.0.
    assert control["found_rate"] > 0.95 and control["median_abs_dx_mm"] == 0 and control["same_page_rate"] == 1.0
    assert all(g["editor_finding"] for g in clean["gap_report"])

    shifted = analyse_pdf(make_document([body_page(1), "", body_page(2), body_page(3)]))
    report = compare_models(model, shifted, include_matches=True)
    result = attribute(model, features, rebuilt, report, None)
    assert result["summary"]["global"][0]["cause"] == "pagination"
    assert result["summary"]["words_by_cause"].get("pagination", 0) > 0


def test_side_by_side_letterhead_becomes_a_column_section():
    # A large title beside smaller details on a raised baseline (DD-443); the tabbed row below shares one size
    # and baseline and must stay a single paragraph.
    page = ("BT /F2 22 Tf 72 720 Td (INVOICE) Tj ET "
            "BT /F1 10 Tf 420 726 Td (Invoice no. 42) Tj ET "
            "BT /F1 10 Tf 420 712 Td (Issue date 01/10) Tj ET "
            "BT /F1 10 Tf 72 640 Td (Bill to) Tj ET BT /F1 10 Tf 420 640 Td (Due on receipt) Tj ET "
            "BT /F1 10 Tf 72 610 Td (Plain body text that runs across the whole width of the content area here.) Tj ET")
    model = analyse_pdf(make_document([page]), label="letterhead.pdf")
    definition = reconstruct(model, detect_features(model))["definition"]
    blocks = definition["blocks"]
    kinds = [b["type"] for b in blocks]
    assert kinds[:3] == ["columns", "text", "column_break"]
    end = kinds.index("columns_end")
    left = blocks[1]["text"]
    right = [b["text"] for b in blocks[3:end]]
    assert left == "INVOICE" and right == ["Invoice no. 42", "Issue date 01/10"]
    # The grid's percentage widths and the gap together fill the content width.
    widths, gap = blocks[0]["widths"], blocks[0]["gap_mm"]
    content = 215.9 - definition["page"]["margin_left_mm"] - definition["page"]["margin_right_mm"]
    assert 0 < gap <= 6 and abs(sum(widths) + gap / content * 100 - 100) < 0.5
    assert any("Bill to" in b.get("text", "") and "Due on receipt" in b.get("text", "") for b in blocks[end:])


def test_bold_totals_row_becomes_a_row_style():
    # DD-448: a wholly bold body row among plain ones maps to table.row_styles instead of a gap.
    page = ""
    for index, (font, item, amount) in enumerate([("F2", "Item", "Amount"), ("F1", "Design", "100.00"),
                                                   ("F1", "Build", "250.00"), ("F1", "Support", "80.00"),
                                                   ("F2", "Total due", "430.00")]):
        y = 700 - 20 * index
        page += (f"BT /{font} 10 Tf 72 {y} Td ({item}) Tj ET BT /{font} 10 Tf 480 {y} Td ({amount}) Tj ET "
                 f"72 {y - 6} 468 0.5 re f ")
    model = analyse_pdf(make_document([page]), label="totals.pdf")
    rebuilt = reconstruct(model, detect_features(model))
    (table,) = [b for b in rebuilt["definition"]["blocks"] if b["type"] == "table"]
    assert table["static_rows"][-1] == ["Total due", "430.00"] and table["row_styles"] == [{"row": 3, "bold": True}]
    assert not [g for g in rebuilt["gaps"] if g["property"] == "row_styles"]
    assert validate_reconstruction(rebuilt, capability_manifest()) == []
    table["row_styles"][0]["underline"] = True
    assert any("unknown item keys ['underline']" in v for v in validate_reconstruction(rebuilt, capability_manifest()))


def test_wrapped_form_header_far_right_line_and_offset_table_cell():
    # DD-449: (1) a line under the last segment of a four-segment header row is a wrapped cell, not a
    # hanging-indent continuation; (2) a one-line paragraph beyond the 63.5 mm indent range starts with a tab
    # to a left stop; (3) a table cell 0.35 mm below its row's other cells stays in that row.
    page = ""
    for y, cells in ((700, [(72, "Party required to"), (230, "Form/Document/"), (350, "Date by which"), (480, "Covered by")]),
                     (688, [(72, "deliver document"), (240, "Certificate"), (350, "to be delivered"), (480, "Section 3(d)")])):
        page += "".join(f"BT /F2 10 Tf {x} {y} Td ({text}) Tj ET " for x, text in cells)
    page += "BT /F1 10 Tf 473 676 Td (Representation) Tj ET "  # regular weight: a bold short line reads as a heading
    page += "BT /F1 10 Tf 350 620 Td ([will][will not] apply to Party B) Tj ET "
    for index, (item, amount) in enumerate([("Design", "100.00"), ("Build", "250.00"), ("Support", "80.00"), ("Total", "430.00")]):
        y = 560 - 20 * index
        page += (f"BT /F1 10 Tf 72 {y} Td ({item}) Tj ET BT /F1 10 Tf 480 {y - (1 if index == 3 else 0)} Td ({amount}) Tj ET "
                 f"72 {y - 6} 468 0.5 re f ")
    model = analyse_pdf(make_document([page]), label="form-header.pdf")
    rebuilt = reconstruct(model, detect_features(model))
    blocks = rebuilt["definition"]["blocks"]
    second = next(b for b in blocks if b.get("text", "").startswith("deliver document"))
    assert second["text"] == "deliver document\tCertificate\tto be delivered\tSection 3(d)" and len(second["tab_stops"]) == 3
    assert any(b.get("text") == "Representation" for b in blocks)
    election = next(b for b in blocks if "apply to Party B" in b.get("text", ""))
    assert election["text"].startswith("\t") and election["left_indent"] == 0
    content_left = rebuilt["definition"]["page"]["margin_left_mm"]
    assert abs(election["tab_stops"][0] / (96 / 25.4) - (350 * 25.4 / 72 - content_left)) < 0.5
    (table,) = [b for b in blocks if b["type"] == "table"]
    assert table["static_rows"][-1] == ["Total", "430.00"] and len(table["static_rows"]) + table["show_header"] == 4
    assert not [g for g in rebuilt["gaps"] if g["feature"] == "tab.positioned_gap"]
    assert validate_reconstruction(rebuilt, capability_manifest()) == []


def test_rich_text_dot_leader_becomes_a_leader_stop():
    # DD-450: a leader in a mixed-style line is a leader tab stop, like plain text, and the runs keep their styles.
    page = ("BT /F2 10 Tf 72 700 Td (Party A:) Tj /F1 10 Tf ( Signed on ..............................) Tj ET "
            "BT /F1 10 Tf 72 680 Td (Plain body text that continues across one line only here.) Tj ET "
            "BT /F2 10 Tf 72 660 Td (Party B:) Tj /F1 10 Tf ( Jurisdiction ..............................]*) Tj ET")
    model = analyse_pdf(make_document([page]), label="rich-leader.pdf")
    rebuilt = reconstruct(model, detect_features(model))
    first, second = [b for b in rebuilt["definition"]["blocks"] if b["type"] == "rich_text"]
    runs = first["paragraphs"][0]["runs"]
    assert [(r["text"], r["style"]["bold"]) for r in runs] == [("Party A:", True), (" Signed on\t", False)]
    (stop,) = first["tab_stops"]
    assert stop["align"] == "left" and stop["leader"] == "dot" and stop["position"] > 48
    # A closing bracket attached to the leader follows the tab; the stop ends before it.
    assert "".join(r["text"] for r in second["paragraphs"][0]["runs"]) == "Party B: Jurisdiction\t]*"
    (stop,) = second["tab_stops"]
    assert stop["leader"] == "dot"
    assert not [g for g in rebuilt["gaps"] if g["feature"] == "tab.dot_leader"]
    assert validate_reconstruction(rebuilt, capability_manifest()) == []
