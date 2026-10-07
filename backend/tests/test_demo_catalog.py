from app.main import STARTER_CATALOG, starter_definition
from app.rendering import render_definition


def test_every_demo_template_has_an_industry_structure_and_complete_sample_data():
    assert len(STARTER_CATALOG) >= 40
    for starter_id, starter in STARTER_CATALOG.items():
        definition = starter_definition(starter_id, "en")
        result = render_definition(definition, starter["sample_data"], "en", "error")
        types = [block.get("type") for block in starter["blocks"]]
        headings = [block.get("text") for block in starter["blocks"] if block.get("type") == "text"]
        assert "table" in types, starter_id
        assert types.count("table") >= 2, starter_id
        assert len(headings) >= 4, starter_id
        assert any(isinstance(text, str) and any(marker in text.casefold()
                   for marker in ("summary", "details", "overview", "review", "policy", "event", "matter"))
                   for text in headings), starter_id
        assert any(isinstance(text, str) and "note" in text.casefold() for text in headings), starter_id
        assert result["missing_fields"] == [], starter_id
        assert result["missing_translations"] == [], starter_id
        assert result["artifact"].startswith("<!doctype html>")


def test_demo_corpus_categories_have_multiple_industry_examples():
    grouped: dict[str, list[str]] = {}
    for starter_id, starter in STARTER_CATALOG.items():
        grouped.setdefault(starter["category"], []).append(starter_id)
    assert len(grouped) >= 10
    assert all(len(starter_ids) >= 3 for starter_ids in grouped.values())
