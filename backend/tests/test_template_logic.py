import base64

import pytest

from app.rendering import render_definition


def test_image_alignment_uses_explicit_pdf_safe_margins():
    source = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    for alignment, margins in {
        "left": "margin-left:0;margin-right:auto;",
        "center": "margin-left:auto;margin-right:auto;",
        "right": "margin-left:auto;margin-right:0;",
    }.items():
        artifact = render_definition({"blocks": [{"type": "image", "src": source, "align": alignment}]})["artifact"]
        assert f"image-align-{alignment} img" in artifact
from app.template_logic import TemplateDataError, TemplateEvaluationLimitError, format_value, generate_sample_data


def test_generated_sample_data_respects_schema_locale_and_template_constructs():
    schema_result = generate_sample_data({"data_schema": {"type": "object", "properties": {
        "customer": {"type": "object", "properties": {"name": {"type": "string"}}},
        "total": {"type": "number"}, "paid": {"type": "boolean"}}}}, "de-DE")
    assert schema_result == {"customer": {"name": "Alex"}, "total": 1234.5, "paid": True}
    result = generate_sample_data({"locale": "de-DE", "blocks": [
        {"type": "text", "text": "{{customer.name}} {{currency(total)}} {{date(issued)}}"},
        {"type": "if", "condition": {"path": "paid", "equals": True}, "then": []},
        {"type": "table", "items": "lines", "columns": [
            {"header": "Description", "path": "description"},
            {"header": "Amount", "path": "amount", "format": "currency"}]},
    ]}, "de-DE")
    assert result["customer"]["name"] == "Alex"
    assert result["total"] == 1234.5 and result["issued"] == "2026-01-15"
    assert result["paid"] is True and result["lines"][0]["amount"] == 1234.5


def test_theme_chart_and_data_background_are_bounded_render_features():
    result = render_definition({"theme": {"accent": "#205448"}, "page": {
        "background": "data:image/png;base64,AA=="}, "blocks": [{"type": "chart", "items": "rows",
        "label_path": "name", "value_path": "amount", "chart_type": "bar"}]},
        {"rows": [{"name": "A", "amount": 2}, {"name": "B", "amount": 1}]})
    assert "--theme-accent:#205448" in result["artifact"]
    assert "template-chart" in result["artifact"] and result["artifact"].count("<rect") >= 2
    assert "background-image:url('data:image/png;base64,AA==')" in result["artifact"]


def test_theme_font_and_spacing_tokens_are_validated_and_applied():
    result = render_definition({"theme": {"font_family": "Georgia", "spacing": "1.8"}, "blocks": [{"type": "text", "text": "Theme"}]}, {})
    assert "--theme-font-family:Georgia" in result["artifact"]
    assert "--theme-spacing:1.8" in result["artifact"]
    fallback = render_definition({"theme": {"font_family": "bad;url(x)", "spacing": "99"}, "blocks": [{"type": "text", "text": "Theme"}]}, {})
    assert "--theme-font-family:bad;url(x)" not in fallback["artifact"]
    assert "--theme-spacing:1.45" in fallback["artifact"]


def test_chart_types_emit_distinct_bounded_svg_geometry():
    data = {"rows": [{"name": "A", "amount": 10}, {"name": "B", "amount": 20}]}
    for chart_type, marker in (("bar", "<rect"), ("line", "<polyline"), ("pie", "<path")):
        result = render_definition({"blocks": [{"type": "chart", "items": "rows",
            "label_path": "name", "value_path": "amount", "chart_type": chart_type}]}, data)
        assert marker in result["artifact"]
        assert "<script" not in result["artifact"]


def test_toc_links_only_to_bounded_declared_anchors():
    result = render_definition({"blocks": [
        {"type": "toc"},
        {"type": "text", "text": "Intro", "toc_label": "Introduction", "anchor_id": "intro", "toc_level": 1},
        {"type": "text", "text": "Unsafe", "toc_label": "Bad", "anchor_id": "javascript:bad"},
    ]})
    assert 'aria-label="Table of contents"' in result["artifact"]
    assert 'href="#intro"' in result["artifact"] and 'id="intro"' in result["artifact"]
    assert 'javascript:bad' not in result["artifact"]


def test_nested_paths_loops_conditions_and_locale_formatting():
    result = render_definition({
        "locale": "de-DE", "blocks": [
            {"type": "text", "text": "{{customer.name}} {{currency(total)}}"},
            {"type": "if", "condition": {"path": "paid", "truthy": True},
             "then": [{"type": "text", "text": "paid"}], "else": [{"type": "text", "text": "due"}]},
            {"type": "loop", "items": "lines", "as": "line", "empty": "none",
             "blocks": [{"type": "text", "text": "{{line.label}} {{number(line.amount)}}"}]},
        ]
    }, {"customer": {"name": "Sam"}, "total": 12.5, "paid": True,
       "lines": [{"label": "A", "amount": 2}, {"label": "B", "amount": 3}]})
    assert "Sam" in result["artifact"] and "12,50 €" in result["artifact"]
    assert "paid" in result["artifact"] and "A 2" in result["artifact"]


def test_missing_field_policy_is_explicit():
    definition = {"blocks": [{"type": "text", "text": "Hi {{customer.email}}"}]}
    assert "[[customer.email]]" in render_definition(definition, {}, missing_policy="placeholder")["artifact"]
    with pytest.raises(TemplateDataError):
        render_definition({**definition, "missing_policy": "error"}, {})


def test_locale_profiles_cover_grouping_currency_and_date_examples():
    from app.template_logic import format_value
    assert format_value(1234.5, "en-US", "number") == "1,234.5"
    assert format_value(1234.5, "de-DE", "currency") == "1.234,50 €"
    assert format_value(1234567.8, "hi-IN", "number") == "12,34,567.8"
    assert format_value(1234.5, "fr-FR", "number") == "1\u202f234,5"
    assert format_value("2026-09-24", "de-DE", "date") == "24/09/2026"
    assert format_value("2026-09-24", "ja-JP", "date") == "2026/09/24"


def test_all_shipped_preview_locales_have_explicit_currency_profiles():
    expected = {
        "en": "$1,234.50", "en-GB": "£1,234.50", "de-DE": "1.234,50 €",
        "ar": "1٬234٫50 د.إ", "hi": "₹1,234.50", "th": "฿1,234.50",
        "zh-CN": "¥1,234.50", "ja-JP": "¥1,234.50", "ko": "₩1,234.50",
    }
    expected = {
        "en": "$1,234.50", "en-GB": "£1,234.50", "de-DE": "1.234,50 €",
        "ar": "١٬٢٣٤٫٥٠ د.إ", "hi": "₹1,234.50", "th": "฿1,234.50",
        "zh-CN": "¥1,234.50", "ja-JP": "¥1,234.50", "ko": "₩1,234.50",
    }
    for locale, value in expected.items():
        assert format_value(1234.5, locale, "currency") == value


def test_arabic_indic_number_and_percent_digits_follow_locale_profile():
    from app.template_logic import format_value
    assert format_value(1234.5, "ar-EG", "number") == "١٬٢٣٤٫٥"
    assert format_value(0.125, "ar-EG", "percent") == "١٢٫٥٪"


def test_editor_styles_are_bounded_and_persist_in_server_render():
    result = render_definition({"blocks": [{"type": "text", "text": "Styled", "bold": True,
                                             "italic": True, "color": "#123456", "font_size": 18,
                                             "align": "center", "font_family": "Noto Sans"}]})
    assert 'style="color:#123456;font-size:18px;font-weight:700;font-style:italic;text-align:center;font-family:Noto Sans"' in result["artifact"]
    unsafe = render_definition({"blocks": [{"type": "text", "text": "Safe", "color": "red;body{display:none}", "font_size": 200}]})
    assert 'style=' not in unsafe["artifact"]


def test_repeat_table_follows_data_and_repeats_header_for_print_layout():
    result = render_definition({"blocks": [{"type": "text", "text": "Before"}, {"type": "table", "items": "lines",
                                             "columns": [{"header": "Description", "path": "description"},
                                                          {"header": "Amount", "path": "amount", "format": "currency"}]},
                                             {"type": "text", "text": "After"}]},
                               {"lines": [{"description": "One", "amount": 2}, {"description": "Two", "amount": 3}]})
    artifact = result["artifact"]
    assert artifact.index("Before") < artifact.index('<table class="template-table"') < artifact.index("After")
    assert artifact.count("<tbody><tr>") == 1
    assert artifact.count("<tr>") == 3
    assert artifact.count("<th scope=\"col\" dir=\"auto\">Description</th>") == 1
    assert "One" in artifact and "Two" in artifact and "2.00" in artifact
    assert "display:table-header-group" in artifact


def test_repeat_and_conditional_blocks_follow_editor_logic_contract():
    result = render_definition({"blocks": [
        {"type": "loop", "items": "rows", "as": "row", "blocks": [{"type": "text", "text": "{{row.description}}"}]},
        {"type": "if", "condition": {"path": "show_note", "equals": True},
         "then": [{"type": "text", "text": "shown"}], "else": [{"type": "text", "text": "hidden"}]},
    ]}, {"rows": [{"description": "one"}, {"description": "two"}], "show_note": True})
    assert result["artifact"].count("one") == 1
    assert result["artifact"].count("two") == 1
    assert "shown" in result["artifact"] and "hidden" not in result["artifact"]


def test_page_settings_emit_bounded_size_orientation_margins_and_repeated_chrome():
    result = render_definition({"page": {"size": "Letter", "orientation": "landscape", "margin_mm": 25,
                                         "header": "{{title}}", "footer": "Confidential", "show_page_numbers": True},
                               "blocks": [{"type": "text", "text": "Body"}]}, {"title": "Report"})
    artifact = result["artifact"]
    assert "@page{size:Letter landscape;margin:25mm;" in artifact
    assert '<header dir="auto" class="document-header">Report</header>' in artifact
    assert '<footer dir="auto" class="document-footer">Confidential <span class="page-number">Page </span></footer>' in artifact
    assert ".page-number::after{content:counter(page);}" in artifact
    with pytest.raises(ValueError, match="page.size"):
        render_definition({"page": {"size": "Tabloid"}, "blocks": []})


def test_preview_locale_override_controls_html_language_and_formatting():
    result = render_definition({"locale": "en", "blocks": [{"type": "text", "text": "{{date(issued)}} {{currency(total)}}"}]},
                               {"issued": "2026-09-24", "total": 12.5}, locale="de-DE")
    assert '<html lang="de-DE" dir="ltr">' in result["artifact"]
    assert "24/09/2026" in result["artifact"] and "12,50 €" in result["artifact"]


def test_candidate_output_carries_bounded_document_metadata():
    result = render_definition({"name": "Invoice", "metadata": {"title": "Quarterly <report>", "author": "Finance"},
                                "blocks": [{"type": "text", "text": "Body"}]}, locale="de-DE")
    assert "<title>Quarterly &lt;report&gt;</title>" in result["artifact"]
    assert '<meta name="author" content="Finance">' in result["artifact"]
    assert result["metadata"] == {"title": "Quarterly <report>", "author": "Finance", "language": "de-DE"}


def test_mixed_direction_content_has_locale_direction_and_auto_boundaries():
    result = render_definition({"locale": "ar", "page": {"header": "رقم 123 / Ref"}, "blocks": [
        {"type": "text", "text": "العربية Ref 123 (A-1)"},
        {"type": "table", "items": "rows", "columns": [{"header": "الوصف / Description", "path": "value"}]},
    ]}, {"rows": [{"value": "עברית / 45"}]})
    assert '<html lang="ar" dir="rtl">' in result["artifact"]
    assert '<p dir="auto">العربية Ref 123 (A-1)</p>' in result["artifact"]
    assert '<th scope="col" dir="auto">الوصف / Description</th>' in result["artifact"]
    assert '<td dir="auto">עברית / 45</td>' in result["artifact"]
    assert 'class="document-header"' in result["artifact"]


def test_template_translation_map_selects_locale_and_reports_missing_keys():
    definition = {"translations": {"en": {"greeting": "Hello"}, "de": {"greeting": "Hallo"}},
                  "blocks": [{"type": "text", "translation_key": "greeting", "text": "Fallback"},
                             {"type": "loop", "items": "rows", "as": "row", "blocks": [
                                 {"type": "text", "translation_key": "missing.label", "text": "Row {{row.name}}"}]}]}
    german = render_definition(definition, {"rows": [{"name": "A"}]}, locale="de-DE")
    assert "Hallo" in german["artifact"] and "Row A" in german["artifact"]
    assert german["missing_translations"] == ["de-DE:missing.label"]
    english = render_definition(definition, {"rows": [{"name": "A"}]}, locale="en")
    assert "Hello" in english["artifact"] and english["missing_translations"] == ["en:missing.label"]
    with pytest.raises(ValueError, match="translation_key"):
        render_definition({"blocks": [{"type": "text", "translation_key": "bad key", "text": "x"}]})


def test_page_flow_controls_emit_break_and_keep_together_rules():
    result = render_definition({"blocks": [{"type": "text", "text": "Heading", "break_before": True, "keep_together": True},
                                             {"type": "table", "items": "rows", "break_before": True, "keep_together": True,
                                              "columns": [{"header": "Name", "path": "name"}]}]},
                               {"rows": [{"name": "A"}]})
    artifact = result["artifact"]
    assert 'style="break-before:page;break-inside:avoid"' in artifact
    assert '<table class="template-table page-break-before keep-together">' in artifact
    assert '.page-break-before{break-before:page;page-break-before:always;}' in artifact
    assert 'orphans:3;widows:3' in artifact
    assert 'page-break-before:always' in artifact
    assert 'page-break-inside:avoid' in artifact
    assert 'table.template-table tr{break-inside:avoid;page-break-inside:avoid;}' in artifact


def test_image_blocks_support_bounded_fixed_and_bound_base64_sources():
    pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    result = render_definition({"blocks": [{"type": "image", "src": "{{logo}}", "alt": "Brand", "width": 120}]},
                               {"logo": pixel})
    artifact = result["artifact"]
    assert '<figure class="template-image image-align-left" style="text-align:left"><img' in artifact
    assert 'style="display:inline-block;width:120px"' in artifact
    assert 'alt="Brand"' in artifact and pixel in artifact


def test_image_alignment_is_emitted_as_bounded_figure_margins():
    centered = render_definition({"blocks": [{"type": "image", "src": "data:image/png;base64,AA==", "align": "center"}]})["artifact"]
    right = render_definition({"blocks": [{"type": "image", "src": "data:image/png;base64,AA==", "align": "right"}]})["artifact"]
    assert '<figure class="template-image image-align-center" style="text-align:center">' in centered
    assert '<figure class="template-image image-align-right" style="text-align:right">' in right


def test_image_blocks_reject_external_sources_by_default():
    with pytest.raises(ValueError, match="base64 image"):
        render_definition({"blocks": [{"type": "image", "src": "https://example.test/logo.png"}]})


@pytest.mark.parametrize("markup", [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.test/x" /></svg>',
    '<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"></svg>',
])
def test_image_blocks_reject_unsafe_svg_markup(markup):
    source = "data:image/svg+xml;base64," + base64.b64encode(markup.encode()).decode()
    with pytest.raises(ValueError, match="unsafe markup"):
        render_definition({"blocks": [{"type": "image", "src": source}]})


def test_image_blocks_accept_safe_bounded_svg():
    markup = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1" fill="#205448" /></svg>'
    source = "data:image/svg+xml;base64," + base64.b64encode(markup.encode()).decode()
    assert source in render_definition({"blocks": [{"type": "image", "src": source}]})["artifact"]


def test_image_sources_cover_base64_uploaded_asset_and_explicit_url(tmp_path):
    pixel = b"\x89PNG\r\n\x1a\n" + b"fixture"
    direct = render_definition({"blocks": [{"type": "image", "src": "data:image/png;base64,AA=="}]})
    assert "data:image/png;base64,AA==" in direct["artifact"]
    asset = render_definition({"blocks": [{"type": "image", "src": "/api/assets/0123456789abcdef0123456789abcdef.png"}]})
    assert "/api/assets/0123456789abcdef0123456789abcdef.png" in asset["artifact"]
    external = render_definition({"allow_external_sources": True, "allowed_image_hosts": ["cdn.example.test"],
                                  "blocks": [{"type": "image", "src": "https://cdn.example.test/logo.png"}]})
    assert "https://cdn.example.test/logo.png" in external["artifact"]
    with pytest.raises(ValueError, match="base64 image"):
        render_definition({"allow_external_sources": True, "allowed_image_hosts": [],
                           "blocks": [{"type": "image", "src": "https://cdn.example.test/logo.png"}]})

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from app.main import create_app
    from app.models import Base
    from app.storage import LocalStore
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        unsafe_svg = b'<svg><script>alert(1)</script></svg>'
        rejected = client.post("/api/assets?filename=unsafe.svg", content=unsafe_svg,
                               headers={"content-type": "image/svg+xml"})
        assert rejected.status_code == 415
        uploaded = client.post("/api/assets?filename=logo.png", content=pixel, headers={"content-type": "image/png"})
        assert uploaded.status_code == 201, uploaded.text
        body = uploaded.json()
        fetched = client.get(body["url"])
        assert fetched.status_code == 200 and fetched.headers["content-type"].startswith("image/png")
        assert fetched.content == pixel


def test_code_blocks_render_qr_code128_and_ean13_svg_from_bound_values():
    result = render_definition({"blocks": [
        {"type": "code", "code_type": "qr", "value": "{{order.id}}"},
        {"type": "code", "code_type": "code128", "value": "{{order.code}}"},
        {"type": "code", "code_type": "ean13", "value": "{{order.ean}}"},
    ]}, {"order": {"id": "A-123", "code": "ABC123", "ean": "5901234123457"}})
    artifact = result["artifact"]
    assert artifact.count('<figure class="template-code"') == 3
    assert artifact.count("<svg") == 3
    assert "aria-label=\"qr code\"" in artifact
    assert artifact.count("<path") + artifact.count("<rect") > 0
    assert "<script" not in artifact.lower() and "javascript:" not in artifact.lower()


def test_code_blocks_reject_invalid_ean_values():
    for value in ("123", "5901234123456"):
        with pytest.raises(ValueError, match="EAN-13"):
            render_definition({"blocks": [{"type": "code", "code_type": "ean13", "value": value}]})


@pytest.mark.parametrize("value", ["", "x" * 201])
def test_code_blocks_reject_empty_or_oversized_values(value):
    with pytest.raises(ValueError, match="between 1 and 200"):
        render_definition({"blocks": [{"type": "code", "code_type": "qr", "value": value}]})


def test_render_result_exposes_bounded_font_diagnostics_without_claiming_embedding():
    result = render_definition({"blocks": [{"type": "text", "text": "العربية 中文"}]})
    report = {item["script"]: item for item in result["font_report"]}
    assert {"arabic", "cjk"}.issubset(report)
    assert report["arabic"]["embedded_fonts"] == []
    assert report["cjk"]["status"] == "candidate"


def test_font_diagnostics_warn_for_unmapped_symbol_without_claiming_embedding():
    result = render_definition({"blocks": [{"type": "text", "text": "Hello 😀"}]})
    report = {item["script"]: item for item in result["font_report"]}
    assert result["missing_glyphs"] == ["U+1F600"]
    assert report["latin"]["missing_glyphs"] == ["U+1F600"]
    assert report["latin"]["status"] == "warning"
    assert report["latin"]["embedded_fonts"] == []


def test_unsafe_expression_is_rejected():
    hostile = [
        "{{__import__('os')}}",
        "{{customer.__class__}}",
        "{{open('secret.txt')}}",
        "{{(1 + 1)}}",
        "{{customer.name()}}",
    ]
    for expression in hostile:
        with pytest.raises(ValueError, match="Unsupported template expression"):
            render_definition({"blocks": [{"type": "text", "text": expression}]}, {"customer": {"name": "Sam"}})


def test_template_data_is_html_escaped_and_conditions_cannot_invoke_code():
    result = render_definition({"blocks": [{"type": "text", "text": "{{value}}"}]},
                               {"value": "<script>fetch('/secret')</script>"})
    assert "&lt;script&gt;fetch(&#x27;/secret&#x27;)&lt;/script&gt;" in result["artifact"]
    with pytest.raises(ValueError, match="Unsupported template expression"):
        render_definition({"blocks": [{"type": "if", "condition": {"path": "os.system('id')", "truthy": True},
                                         "then": [{"type": "text", "text": "bad"}]}]}, {})


def test_schema_validation_reports_field_paths():
    with pytest.raises(ValueError, match="Render data failed schema validation"):
        render_definition({"data_schema": {"type": "object", "required": ["id"],
                                           "properties": {"id": {"type": "string"}}},
                           "blocks": []}, {})


def test_comparisons_dates_and_evaluation_limits_are_bounded():
    definition = {"locale": "en-GB", "blocks": [
        {"type": "text", "text": "{{date(issued)}}"},
        {"type": "if", "condition": {"path": "total", "greater_than": 10},
         "then": [{"type": "text", "text": "large"}]},
    ]}
    result = render_definition(definition, {"issued": "2026-09-23", "total": 12})
    assert "23/09/2026" in result["artifact"] and "large" in result["artifact"]

    with pytest.raises(TemplateEvaluationLimitError, match="Loop exceeds"):
        render_definition({"blocks": [{"type": "loop", "items": "rows", "blocks": []}]},
                         {"rows": list(range(1001))})
