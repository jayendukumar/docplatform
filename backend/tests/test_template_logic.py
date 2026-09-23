import pytest

from app.rendering import render_definition
from app.template_logic import TemplateDataError


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


def test_unsafe_expression_is_rejected():
    with pytest.raises(ValueError, match="Unsupported template expression"):
        render_definition({"blocks": [{"type": "text", "text": "{{__import__('os')}}"}]}, {})


def test_schema_validation_reports_field_paths():
    with pytest.raises(ValueError, match="Render data failed schema validation"):
        render_definition({"data_schema": {"type": "object", "required": ["id"],
                                           "properties": {"id": {"type": "string"}}},
                           "blocks": []}, {})
