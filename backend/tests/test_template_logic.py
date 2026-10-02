import base64

import pytest

from app.rendering import render_definition


def test_page_owned_surfaces_fill_the_content_area_inside_page_margins():
    # DD-422: a surface sized to the full page height overflowed onto an extra page whenever margins were set.
    for size, height in (("Letter", 279), ("A4", 297)):
        artifact = render_definition({
            "page": {"size": size, "orientation": "portrait", "margin_top_mm": 32.2, "margin_bottom_mm": 27.6,
                     "margin_left_mm": 25, "margin_right_mm": 25},
            "blocks": [{"type": "text", "text": "One", "page_number": 1}, {"type": "text", "text": "Two", "page_number": 2}],
        })["artifact"]
        assert f"height:{height - 32.2 - 27.6:g}mm;overflow:hidden;box-sizing:border-box;" in artifact
    landscape = render_definition({
        "page": {"size": "A4", "orientation": "landscape", "margin_mm": 10},
        "blocks": [{"type": "text", "text": "One", "page_number": 1}],
    })["artifact"]
    assert "height:190mm;overflow:hidden" in landscape


def test_page_owned_absolute_blocks_are_scoped_to_relative_page_surfaces():
    result = render_definition({"blocks": [
        {"type": "text", "text": "Page one", "page_number": 1, "position_mode": "absolute", "position_unit": "mm", "position_x": 10, "position_y": 20},
        {"type": "text", "text": "Page two", "page_number": 2, "position_mode": "absolute", "position_unit": "mm", "position_x": 12, "position_y": 22},
    ]})
    artifact = result["artifact"]
    assert artifact.count('class="page-surface') == 2
    assert 'class="page-surface" data-page-number="1"' in artifact
    assert 'class="page-surface page-break-before" data-page-number="2"' in artifact
    assert artifact.count("position:absolute") == 2


def test_table_column_widths_are_bounded_and_emitted_as_col_styles():
    result = render_definition({"blocks": [{"type": "table", "items": "rows", "columns": [
        {"header": "Document", "path": "document", "width": 45},
        {"header": "Status", "path": "status", "width": 55},
    ]}]}, {"rows": [{"document": "Tax form", "status": "Yes"}]})
    assert '<col style="width:45%" />' in result["artifact"]
    assert '<col style="width:55%" />' in result["artifact"]
    with pytest.raises(ValueError, match="table column width"):
        render_definition({"blocks": [{"type": "table", "items": "rows", "columns": [
            {"header": "Document", "path": "document", "width": 101},
        ]}]}, {"rows": []})


def test_table_row_condition_filters_rows_without_code():
    result = render_definition({"blocks": [{"type": "table", "items": "rows", "row_condition": {
        "path": "included", "equals": True}, "columns": [
        {"header": "Document", "path": "document"},
    ]}]}, {"rows": [{"document": "Keep", "included": True}, {"document": "Hide", "included": False}]})
    assert ">Keep</td>" in result["artifact"]
    assert ">Hide</td>" not in result["artifact"]


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


def test_chart_type_specific_properties_are_rendered_and_bounded():
    data = {"rows": [{"name": "A", "amount": 10}, {"name": "B", "amount": 20}]}
    horizontal = render_definition({"blocks": [{"type": "chart", "items": "rows",
        "label_path": "name", "value_path": "amount", "chart_type": "bar",
        "chart_orientation": "horizontal", "chart_title": "Revenue",
        "show_grid": False, "show_legend": False, "x_axis_label": "Amount"}]}, data)
    assert 'class="chart-title"' in horizontal["artifact"]
    assert 'class="chart-grid"' not in horizontal["artifact"]
    assert 'class="chart-legend"' not in horizontal["artifact"]
    assert 'Amount' in horizontal["artifact"]

    line = render_definition({"blocks": [{"type": "chart", "items": "rows",
        "label_path": "name", "value_path": "amount", "chart_type": "line",
        "show_points": False}]}, data)
    assert "<polyline" in line["artifact"] and "<circle" not in line["artifact"]

    donut = render_definition({"blocks": [{"type": "chart", "items": "rows",
        "label_path": "name", "value_path": "amount", "chart_type": "pie",
        "donut": True}]}, data)
    assert 'class="chart-donut-hole"' in donut["artifact"]


def test_chart_supports_bound_multiseries_colours_and_static_rows():
    bound = render_definition({"blocks": [{"type": "chart", "items": "rows",
        "label_path": "month", "value_path": "amount", "series_path": "team",
        "chart_type": "bar", "stacked": True, "show_values": True,
        "colors": ["#112233", "#445566"], "background_color": "#fafafa"}]}, {
            "rows": [{"month": "Jan", "team": "A", "amount": 2},
                     {"month": "Jan", "team": "B", "amount": 3}]})
    assert 'fill="#112233"' in bound["artifact"]
    assert 'fill="#445566"' in bound["artifact"]
    assert 'aria-label="A Jan 2"' in bound["artifact"]
    static = render_definition({"blocks": [{"type": "chart", "data_mode": "static",
        "items": "unused", "static_data": [{"label": "Only", "value": 7}],
        "chart_type": "pie"}]}, {})
    assert 'Only 7' in static["artifact"]


def test_rich_text_supports_styles_bindings_and_bounded_conditions():
    result = render_definition({"blocks": [{"type": "rich_text", "paragraphs": [{
        "align": "left", "runs": [
            {"type": "text", "text": "Total: ", "style": {"bold": True, "font_family": "Georgia"}},
            {"type": "binding", "path": "amount", "format": "currency", "currency": "CNY",
             "style": {"color": "#112233"}},
            {"type": "condition", "condition": {"path": "value_x", "operator": "equals", "value": "a",
             "then": [{"type": "text", "text": " approved"}], "else": [{"type": "text", "text": " pending"}]}}
        ]
    }]}]}, {"amount": 12.5, "value_x": "a"})
    assert 'class="rich-text-block"' in result["artifact"]
    assert 'font-weight:700' in result["artifact"] and 'font-family:Georgia' in result["artifact"]
    assert '¥12.5' in result["artifact"] and ' approved' in result["artifact"]
    assert 'pending' not in result["artifact"]


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
    body = result["artifact"].split("<body>", 1)[1]
    assert body.count("one") == 1
    assert body.count("two") == 1
    assert "shown" in result["artifact"] and "hidden" not in result["artifact"]


def test_page_settings_emit_bounded_size_orientation_margins_and_repeated_chrome():
    result = render_definition({"page": {"size": "Letter", "orientation": "landscape", "margin_mm": 25,
                                         "header": "{{title}}", "footer": "Confidential", "show_page_numbers": True},
                               "blocks": [{"type": "text", "text": "Body"}]}, {"title": "Report"})
    artifact = result["artifact"]
    assert "@page{size:Letter landscape;margin:25mm;" in artifact
    # DD-429: printed chrome comes from @page margin boxes; the HTML elements are the screen preview only.
    assert '@top-left{content:"Report";' in artifact and '@bottom-left{content:"Confidential";' in artifact
    assert "@bottom-right{content:counter(page);" in artifact
    assert '<header dir="auto" class="document-header">Report</header>' in artifact
    assert '<footer dir="auto" class="document-footer">Confidential <span class="page-number">1</span></footer>' in artifact
    assert "@media print{.document-header,.document-footer{display:none!important;}}" in artifact
    assert "position:fixed" not in artifact and "counter(page);}" not in artifact.split("@page", 1)[0]
    with pytest.raises(ValueError, match="page.size"):
        render_definition({"page": {"size": "Tabloid"}, "blocks": []})


def test_page_settings_emit_individual_margins():
    artifact = render_definition({"page": {"margin_top_mm": 10, "margin_right_mm": 20,
                                             "margin_bottom_mm": 30, "margin_left_mm": 40},
                                  "blocks": []})["artifact"]
    assert "@page{size:A4 portrait;margin:10mm 20mm 30mm 40mm;" in artifact
    assert "position:fixed" not in artifact


def test_page_furniture_alignment_number_position_format_and_escaping():
    # DD-429
    artifact = render_definition({"page": {
        "size": "Letter", "margin_mm": 20, "header": 'Q3 "draft" </style><b>', "header_align": "center",
        "footer": "ISDA\u00ae 2002", "footer_align": "right", "show_page_numbers": True,
        "page_number_position": "footer-center", "page_number_format": "Page {page} of {pages}",
        "header_footer_font_size": 13.33}, "theme": {"font_family": "Times New Roman, serif"},
        "blocks": [{"type": "text", "text": "Body"}]})["artifact"]
    page_rule = artifact.split("@page", 1)[1].split("}body", 1)[0]
    assert '@top-center{content:"Q3 \\22 draft\\22  \\3c \\2f style\\3e \\3c b\\3e ";' in page_rule
    assert '@bottom-right{content:"ISDA\\ae  2002";' in page_rule
    assert '@bottom-center{content:"Page " counter(page) " of " counter(pages);' in page_rule
    assert "font-family:Times New Roman, serif;font-size:13.33px;text-align:center;" in page_rule
    assert "</style><b>" not in artifact.split("<body>", 1)[0]
    assert '<span class="page-number">Page 1 of 1</span>' in artifact
    shared = render_definition({"page": {"header": "Report", "header_align": "right", "show_page_numbers": True,
                                         "page_number_position": "header-right", "page_number_format": "p. {page}"},
                                "blocks": []})["artifact"]
    assert '@top-right{content:"Report" " " "p\\2e  " counter(page);' in shared
    fallback = render_definition({"page": {"show_page_numbers": True, "page_number_position": "side",
                                           "page_number_format": "x" * 41, "footer_align": "justify",
                                           "header_footer_font_size": 99}, "blocks": []})["artifact"]
    assert "@bottom-right{content:counter(page);font-family:" in fallback and "font-size:12px" in fallback


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


def test_text_layout_controls_emit_bounded_word_like_styles():
    result = render_definition({"blocks": [{"type": "text", "text": "Heading", "line_height": 1.8,
                                             "paragraph_spacing_before": 6, "paragraph_spacing_after": 12,
                                             "first_line_indent": 18, "left_indent": 10, "right_indent": 8,
                                             "tab_stops": [64, 128], "keep_with_next": True, "break_after": True}]})
    artifact = result["artifact"]
    assert 'line-height:1.8' in artifact
    assert 'margin-top:6px' in artifact and 'margin-bottom:12px' in artifact
    assert 'text-indent:18px' in artifact and 'padding-left:10px' in artifact and 'padding-right:8px' in artifact
    assert 'tab-size:' not in artifact  # DD-426: stops are positional, no longer a uniform tab-size
    assert 'break-after:avoid;page-break-after:avoid' in artifact
    assert 'break-after:page;page-break-after:always' in artifact


def test_text_blocks_accept_decimal_font_sizes_and_justify():
    # DD-424 and DD-425
    artifact = render_definition({"blocks": [
        {"type": "text", "text": "Body", "font_size": 13.28, "align": "justify"},
        {"type": "text", "text": "Rounded", "font_size": 13.284999},
        {"type": "text", "text": "Unsafe", "font_size": 7.5, "align": "spread"},
        {"type": "rich_text", "paragraphs": [{"align": "justify", "runs": [{"type": "text", "text": "Rich"}]}]},
    ]})["artifact"]
    assert 'font-size:13.28px;text-align:justify' in artifact
    assert 'font-size:13.28px"' in artifact
    assert 'font-size:7.5px' not in artifact and 'text-align:spread' not in artifact
    assert 'class="rich-text-paragraph" style="text-align:justify' in artifact


def test_header_footer_zones_distances_and_rules():
    # DD-437
    artifact = render_definition({"page": {
        "margin_mm": 25, "header_left": "Quarterly {{t}}", "header_right": "Internal", "header_distance_mm": 11,
        "header_rule": True, "header_rule_offset_mm": 8, "furniture_rule_width": 0.5, "furniture_rule_color": "#336699",
        "footer": "Old", "footer_align": "right", "footer_right": "New", "footer_distance_mm": 12,
        "footer_rule": True, "show_page_numbers": True, "page_number_position": "footer-center"},
        "blocks": []}, {"t": "Report"})["artifact"]
    page_rule = artifact.split("@page", 1)[1].split("}body", 1)[0]
    top = "vertical-align:top;padding-top:11mm;border-bottom:0.5px solid #336699;margin-bottom:8mm;}"
    assert '@top-left{content:"Quarterly Report";' in page_rule and page_rule.count(top) == 3
    assert '@top-center{content:"";' in page_rule   # empty zone kept so the rule spans the width
    assert '@bottom-right{content:"New";' in page_rule and '"Old"' not in page_rule
    assert ("@bottom-center{content:counter(page);font-family:Noto Sans, sans-serif;font-size:12px;text-align:center;"
            "vertical-align:bottom;padding-bottom:12mm;border-top:0.5px solid #336699;margin-top:0mm;}") in page_rule
    assert '<header dir="auto" class="document-header">Quarterly Report   Internal</header>' in artifact
    plain = render_definition({"page": {"header": "Legacy", "header_distance_mm": 500}, "blocks": []})["artifact"]
    assert "@top-left{content:\"Legacy\";font-family:Noto Sans, sans-serif;font-size:12px;text-align:left;}" in plain


def test_header_footer_zone_styles_override_the_shared_size():
    # DD-439
    artifact = render_definition({"page": {
        "header_left": "ACCOUNT STATEMENT", "header_right": "Account 1", "header_footer_font_size": 12,
        "show_page_numbers": True, "page_number_position": "footer-center",
        "zone_styles": {"header_left": {"font_size": 17.33, "bold": True}, "header_right": {"italic": True, "bold": "yes"},
                        "footer_center": {"font_size": 10.67}, "bogus": {"bold": True}, "footer_left": {"font_size": 99}}},
        "blocks": []})["artifact"]
    page_rule = artifact.split("@page", 1)[1].split("}body", 1)[0]
    assert '@top-left{content:"ACCOUNT STATEMENT";font-family:Noto Sans, sans-serif;font-size:17.33px;text-align:left;font-weight:700;}' in page_rule
    assert '@top-right{content:"Account 1";font-family:Noto Sans, sans-serif;font-size:12px;text-align:right;font-style:italic;}' in page_rule
    assert "@bottom-center{content:counter(page);font-family:Noto Sans, sans-serif;font-size:10.67px;" in page_rule
    assert "bogus" not in artifact and "99px" not in artifact


def test_column_sections_split_or_flow_and_close_per_page():
    # DD-435
    artifact = render_definition({"blocks": [
        {"type": "text", "text": "Title", "page_number": 1},
        {"type": "columns", "count": 2, "gap_mm": 6.35, "widths": [47, 47], "rule_color": "#999999",
         "paragraph_spacing_before": 8, "page_number": 1},
        {"type": "text", "text": "Left", "page_number": 1},
        {"type": "column_break", "page_number": 1},
        {"type": "text", "text": "Right", "page_number": 1},
        {"type": "text", "text": "Unclosed", "page_number": 2},
        {"type": "columns", "count": 3, "widths": [10, 20], "page_number": 2},
        {"type": "text", "text": "Flow1", "page_number": 2},
        {"type": "columns_end", "page_number": 2},
        {"type": "column_break", "page_number": 2},
        {"type": "text", "text": "After", "page_number": 2},
    ]})["artifact"]
    page_one, page_two = artifact.split('data-page-number="1">')[1].split('data-page-number="2">')
    assert ('<div class="template-columns" style="display:grid;grid-template-columns:47% 47%;column-gap:3.175mm;'
            'align-items:start;margin-top:8px"><div class="template-column" style="min-width:0"><p dir="auto">Left</p></div>'
            '<div class="template-column" style="min-width:0;border-left:1px solid #999999;padding-left:3.175mm">'
            '<p dir="auto">Right</p></div></div>') in page_one   # an open section closes at the end of its page
    assert page_two.startswith('<p dir="auto" style="break-before:page">Unclosed</p>')
    assert ('<div class="template-columns template-columns-flow" style="column-count:3;column-gap:6mm;'
            'column-fill:balance"><p dir="auto">Flow1</p></div><p dir="auto">After</p>') in page_two


def test_shapes_render_lines_and_rectangles():
    # DD-433
    artifact = render_definition({"page": {"margin_mm": 20}, "blocks": [
        {"type": "text", "text": "Body", "page_number": 1},
        {"type": "shape", "shape": "rectangle", "position_mode": "absolute", "position_x": 0, "position_y": 10,
         "width_mm": 165, "height_mm": 6.35, "fill_color": "#d9d9d9", "stroke_width": 0, "layer": "behind", "page_number": 1},
        {"type": "shape", "shape": "line", "position_mode": "absolute", "position_x": 5, "position_y": 40,
         "width_mm": 165, "stroke_width": 0.5, "stroke_style": "dotted", "stroke_color": "#112233", "page_number": 1},
        {"type": "shape", "shape": "line", "orientation": "vertical", "height_mm": 20, "paragraph_spacing_before": 6,
         "page_number": 1},
        {"type": "shape", "shape": "rectangle", "width_mm": 9, "height_mm": 9, "stroke_color": "javascript:x",
         "fill_color": "red", "stroke_style": "wavy", "position_mode": "absolute", "position_x": 900, "page_number": 1},
    ]})["artifact"]
    shapes = [part.split("</div>")[0] for part in artifact.split('<div class="template-shape')[1:]]
    assert ('-rectangle" aria-hidden="true" style="box-sizing:border-box;display:block;width:165mm;height:6.35mm;'
            'background:#d9d9d9;position:absolute;left:0mm;top:10mm;z-index:-1">') in shapes[0]
    assert "border-top:0.5px dotted #112233;position:absolute;left:5mm;top:40mm" in shapes[1]
    assert "height:20mm;width:0;border-left:1px solid #000000;margin-top:6px;margin-bottom:0px" in shapes[2]
    assert "border:1px solid #000000" in shapes[3] and "background" not in shapes[3] and "left:0mm" in shapes[3]
    assert "javascript" not in artifact and ".page-surface{position:relative;z-index:0;" in artifact
    with pytest.raises(ValueError, match="shape"):
        render_definition({"blocks": [{"type": "shape", "shape": "star"}]})


def test_static_tables_typography_alignment_and_rules():
    # DD-431
    artifact = render_definition({"blocks": [{
        "type": "table", "data_mode": "static", "font_size": 13.33, "font_family": "Arial, sans-serif",
        "borders": "horizontal", "border_color": "#000000", "border_width": 0.5, "cell_padding_x": 4,
        "cell_padding_y": 0, "row_height": 26.67, "header_background": "#d9d9d9", "header_bold": False,
        "paragraph_spacing_before": 10, "columns": [{"header": "Description"}, {"header": "Amount", "align": "right"}],
        "static_rows": [["Fees", "{{total}}"], ["<b>x</b>"]]}]}, {"total": "1,250.00"})["artifact"]
    table = artifact[artifact.index("<table"):artifact.index("</table>")]
    assert 'style="font-family:Arial, sans-serif;font-size:13.33px;margin-top:10px"' in table
    cell = "border:0;border-bottom:0.5px solid #000000;padding:0px 4px;box-sizing:border-box;height:26.67px"
    assert f'<th scope="col" dir="auto" style="{cell};font-weight:400;background:#d9d9d9;text-align:right">Amount</th>' in table
    assert f'<td dir="auto" style="{cell};text-align:right">1,250.00</td>' in table
    assert "&lt;b&gt;x&lt;/b&gt;" in table and table.count("<tr>") == 3   # header + two rows; short row padded
    # DD-441: a header row may have its own height, also border-box.
    sized = render_definition({"blocks": [{"type": "table", "data_mode": "static", "row_height": 26.67,
                                           "header_row_height": 24, "columns": [{"header": "A"}], "static_rows": [["x"]]}]})["artifact"]
    assert 'style="box-sizing:border-box;height:26.67px;height:24px">A</th>' in sized
    assert 'style="box-sizing:border-box;height:26.67px">x</td>' in sized
    assert "table-header-gap" not in sized
    # DD-445: space after the header is a spacer row inside <thead>, so it repeats with the header.
    spaced = render_definition({"blocks": [{"type": "table", "data_mode": "static", "header_spacing_after": 5.2,
                                            "columns": [{"header": "A"}, {"header": "B"}],
                                            "static_rows": [["x", "y"]]}]})["artifact"]
    head = spaced[spaced.index("<thead>"):spaced.index("</thead>")]
    assert ('<tr class="table-header-gap" aria-hidden="true"><td colspan="2" '
            'style="height:5.2px;padding:0;border:0;background:none"></td></tr>') in head
    for bad in (0, -3, 241, "5", True):
        rendered = render_definition({"blocks": [{"type": "table", "data_mode": "static", "header_spacing_after": bad,
                                                  "columns": [{"header": "A"}], "static_rows": [["x"]]}]})["artifact"]
        assert "table-header-gap" not in rendered
    headless = render_definition({"blocks": [{"type": "table", "data_mode": "static", "show_header": False,
                                              "header_spacing_after": 8, "columns": [{"header": "A"}],
                                              "static_rows": [["x"]]}]})["artifact"]
    assert "table-header-gap" not in headless


def test_table_row_styles_style_one_body_row_each():
    # DD-447: per-row bold, italic, shading and colour on each cell of the row; -1 is the last body row.
    artifact = render_definition({"blocks": [{
        "type": "table", "data_mode": "static", "cell_padding_x": 4, "cell_padding_y": 0,
        "columns": [{"header": "Item"}, {"header": "Amount", "align": "right"}],
        "static_rows": [["Fees", "100"], ["Costs", "20"], ["Total", "120"]],
        "row_styles": [{"row": -1, "bold": True, "background": "#eeeeee"}, {"row": 0, "italic": True, "color": "#336699"},
                       {"row": -1, "bold": False}, {"row": 3, "bold": True}, {"row": True, "bold": True},
                       {"row": 1.0, "bold": True}, {"row": 1, "background": "red", "color": "#12345"}, "x"]}]})["artifact"]
    body = artifact[artifact.index("<tbody>"):artifact.index("</tbody>")]
    assert '<td dir="auto" style="padding:0px 4px;font-weight:400;background:#eeeeee">Total</td>' in body
    assert '<td dir="auto" style="padding:0px 4px;font-weight:400;background:#eeeeee;text-align:right">120</td>' in body
    assert '<td dir="auto" style="padding:0px 4px;font-style:italic;color:#336699">Fees</td>' in body
    # Out-of-range rows, non-integer rows and invalid colours are ignored, so row 1 is unstyled.
    assert '<td dir="auto" style="padding:0px 4px">Costs</td>' in body
    assert "font-weight" not in artifact[artifact.index("<thead>"):artifact.index("</thead>")]
    bound = render_definition({"blocks": [{"type": "table", "items": "lines", "row_styles": [{"row": -1, "bold": True}],
                                           "columns": [{"header": "A", "path": "a"}]}]},
                              {"lines": [{"a": "x"}, {"a": "y"}]})["artifact"]
    assert '<td dir="auto">x</td>' in bound and '<td dir="auto" style="font-weight:700">y</td>' in bound
    plain = render_definition({"blocks": [{"type": "table", "data_mode": "static", "row_styles": "bold",
                                           "columns": [{"header": "A"}], "static_rows": [["x"]]}]})["artifact"]
    assert '<td dir="auto">x</td>' in plain


def test_absolute_text_spans_to_the_right_edge_so_alignment_works():
    # DD-441: absolutely positioned text is a text box from its left edge to the content area's right edge.
    artifact = render_definition({"blocks": [{"type": "text", "text": "Centred note", "align": "center",
                                              "position_mode": "absolute", "position_unit": "mm",
                                              "position_x": 0, "position_y": 200}]})["artifact"]
    assert "text-align:center;position:absolute;left:0mm;top:200mm;right:0" in artifact
    headless = render_definition({"blocks": [{"type": "table", "data_mode": "static", "show_header": False,
                                              "borders": "none", "columns": [{"header": "A"}],
                                              "static_rows": [["only"]]}]})["artifact"]
    assert "<thead>" not in headless and 'style="border:0">only</td>' in headless
    plain = render_definition({"blocks": [{"type": "table", "items": "rows", "columns": [{"header": "A", "path": "a"}]}]},
                              {"rows": [{"a": "x"}]})["artifact"]
    assert '<td dir="auto">x</td>' in plain   # unstyled tables keep the stylesheet defaults
    for bad in ([["a", "b"]], "rows", [[1]] * 1001):
        with pytest.raises(ValueError, match="static"):
            render_definition({"blocks": [{"type": "table", "data_mode": "static", "columns": [{"header": "A"}],
                                           "static_rows": bad}]})


def test_rich_text_layout_applies_once_and_line_height_follows_run_size():
    # DD-428: block layout went on both the section and every paragraph, and paragraphs inherited the 16 px
    # page default, so line-height multiples were computed against the wrong size.
    artifact = render_definition({"blocks": [{
        "type": "rich_text", "line_height": 1.18, "paragraph_spacing_before": 10, "left_indent": 47,
        "keep_with_next": True, "position_mode": "absolute", "position_x": 5, "position_y": 6, "position_unit": "mm",
        "paragraphs": [{"runs": [{"type": "text", "text": "(b) ", "style": {"font_size": 13.28}},
                                 {"type": "condition", "condition": {"operator": "truthy", "path": "x",
                                                                     "then": [{"type": "text", "text": "Big", "style": {"font_size": 20}}]}}]},
                       {"runs": [{"type": "text", "text": "No explicit size"}]}],
    }]}, {"x": True})["artifact"]
    section = artifact.split('<section class="rich-text-block" style="', 1)[1].split('"', 1)[0]
    assert "position:absolute" in section and "break-after:avoid" in section
    assert "margin-top" not in section and "padding-left" not in section and "line-height" not in section
    first, second = artifact.split('<p class="rich-text-paragraph" style="')[1:3]
    first, second = first.split('"', 1)[0], second.split('"', 1)[0]
    assert "font-size:20px" in first and "line-height:1.18" in first
    assert first.count("margin-top:10px") == 1 and first.count("padding-left:47px") == 1
    assert "font-size" not in second and "line-height:1.18" in second


def test_tab_stops_position_segments_with_alignment_and_leaders():
    # DD-426
    from app.rendering import tab_stops, tabbed_html

    assert tab_stops({"tab_stops": [48, {"position": 300, "align": "right", "leader": "dot"}, {"position": 5000},
                                    "x", True, {"position": 120, "align": "center", "leader": "wavy"}]}) == [
        {"position": 48.0, "align": "left", "leader": "none"},
        {"position": 120.0, "align": "left", "leader": "none"},
        {"position": 300.0, "align": "right", "leader": "dot"}]
    stops = [{"position": 48, "align": "left", "leader": "none"}, {"position": 400, "align": "right", "leader": "dot"}]
    assert tabbed_html(["(a)", "Fees", "1,250.00", "extra"], stops) == (
        '<span class="tab-box" style="width:48px">(a)<span class="tab-fill leader-none"></span></span>'
        '<span class="tab-box" style="width:352px">Fees<span class="tab-fill leader-dot"></span>1,250.00</span>'
        '\textra')
    # The first-line indent moves the first boundary; stops at or before it are skipped.
    assert tabbed_html(["x", "y"], [{"position": 20, "align": "left", "leader": "none"},
                                    {"position": 60, "align": "left", "leader": "none"}], 30) == (
        '<span class="tab-box" style="width:30px">x<span class="tab-fill leader-none"></span></span>y')
    artifact = render_definition({"blocks": [
        {"type": "text", "text": "Name:\t", "tab_stops": [{"position": 500, "leader": "underscore"}]},
        {"type": "text", "text": "<b>\tsafe", "tab_stops": [64]},
        {"type": "rich_text", "tab_stops": [36], "paragraphs": [{"runs": [
            {"type": "text", "text": "(i)\t", "style": {"bold": True}}, {"type": "text", "text": "clause"}]}]},
        {"type": "text", "text": "no\tstops"},
    ]})["artifact"]
    assert '<span class="tab-box" style="width:500px">Name:<span class="tab-fill leader-underscore"></span></span>' in artifact
    assert '&lt;b&gt;<span class="tab-fill' in artifact and "<b>" not in artifact.split("<body>")[1]
    assert ('<span class="tab-box" style="width:36px"><span style="font-weight:700">(i)</span>'
            '<span class="tab-fill leader-none"></span></span>') in artifact
    assert '<p dir="auto">no\tstops</p>' in artifact
    assert ".leader-dot{border-bottom:1px dotted currentColor;}" in artifact


def test_text_layout_controls_ignore_unsafe_values():
    result = render_definition({"blocks": [{"type": "text", "text": "Safe", "line_height": 9,
                                             "paragraph_spacing_after": -4, "first_line_indent": 999,
                                             "tab_stops": [1]}]})
    artifact = result["artifact"]
    assert 'line-height:9' not in artifact
    assert 'margin-bottom:-4px' not in artifact
    assert 'text-indent:999px' not in artifact
    assert 'tab-size:' not in artifact


def test_text_fields_support_bounded_absolute_page_positioning():
    result = render_definition({"blocks": [{"type": "text", "text": "Party A", "position_mode": "absolute", "position_x": 120, "position_y": 240}]})
    artifact = result["artifact"]
    assert 'position:absolute' in artifact and 'left:120px' in artifact and 'top:240px' in artifact

    unsafe = render_definition({"blocks": [{"type": "text", "text": "Safe", "position_mode": "absolute", "position_x": 9999, "position_y": -4}]})
    unsafe_artifact = unsafe["artifact"]
    assert 'left:1200px' in unsafe_artifact and 'top:0px' in unsafe_artifact


def test_text_fields_can_target_later_pages():
    result = render_definition({"blocks": [{"type": "text", "text": "Page one", "page_number": 1},
                                             {"type": "text", "text": "Page three", "page_number": 3}]})
    assert 'Page one' in result["artifact"] and 'Page three' in result["artifact"]
    assert 'Page three' in result["artifact"]
    assert 'break-before:page' in result["artifact"]


def test_image_blocks_support_bounded_fixed_and_bound_base64_sources():
    pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    result = render_definition({"blocks": [{"type": "image", "src": "{{logo}}", "alt": "Brand", "width": 120}]},
                               {"logo": pixel})
    artifact = result["artifact"]
    assert '<figure class="template-image image-align-left" style="text-align:left"><img' in artifact
    assert 'style="display:block;margin-left:0;margin-right:auto;width:120px"' in artifact
    assert 'alt="Brand"' in artifact and pixel in artifact


def test_image_alignment_is_emitted_as_bounded_figure_margins():
    centered = render_definition({"blocks": [{"type": "image", "src": "data:image/png;base64,AA==", "align": "center"}]})["artifact"]
    right = render_definition({"blocks": [{"type": "image", "src": "data:image/png;base64,AA==", "align": "right"}]})["artifact"]
    assert '<figure class="template-image image-align-center" style="text-align:center">' in centered
    assert '<figure class="template-image image-align-right" style="text-align:right">' in right
    assert 'style="display:block;margin-left:auto;margin-right:auto;width:240px"' in centered
    assert 'style="display:block;margin-left:auto;margin-right:0;width:240px"' in right


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
