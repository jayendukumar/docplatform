import pytest

from app.components import ComponentExpansionError, expand_definition


def test_component_update_is_visible_to_every_template_reference():
    registry = {"header": {"blocks": [{"type": "text", "text": "Updated header"}]}}
    first = {"name": "First", "blocks": [{"type": "component", "component_id": "header"}]}
    second = {"name": "Second", "blocks": [{"type": "component", "component_id": "header"}]}

    assert expand_definition(first, registry)["blocks"] == [{"type": "text", "text": "Updated header"}]
    assert expand_definition(second, registry)["blocks"] == [{"type": "text", "text": "Updated header"}]

    registry["header"] = {"blocks": [{"type": "text", "text": "Version two"}]}
    assert expand_definition(first, registry)["blocks"][0]["text"] == "Version two"
    assert expand_definition(second, registry)["blocks"][0]["text"] == "Version two"


def test_component_expansion_allows_repeated_siblings_but_rejects_cycles():
    definition = {"blocks": [
        {"type": "component", "component_id": "header"},
        {"type": "component", "component_id": "header"},
    ]}
    registry = {"header": {"blocks": [{"type": "text", "text": "Header"}]}}
    assert [block["text"] for block in expand_definition(definition, registry)["blocks"]] == ["Header", "Header"]

    with pytest.raises(ComponentExpansionError, match="cycle"):
        expand_definition({"blocks": [{"type": "component", "component_id": "a"}]}, {
            "a": {"blocks": [{"type": "component", "component_id": "b"}]},
            "b": {"blocks": [{"type": "component", "component_id": "a"}]},
        })


def test_page_chrome_can_reference_text_components():
    definition = {"page": {"header_component_id": "header", "footer_component_id": "footer"}, "blocks": []}
    expanded = expand_definition(definition, {
        "header": {"blocks": [{"type": "text", "text": "{{title}}"}]},
        "footer": {"blocks": [{"type": "text", "text": "Confidential"}]},
    })
    assert expanded["page"]["header"] == "{{title}}"
    assert expanded["page"]["footer"] == "Confidential"

    with pytest.raises(ComponentExpansionError, match="text blocks only"):
        expand_definition({"page": {"header_component_id": "header"}, "blocks": []}, {
            "header": {"blocks": [{"type": "table", "items": "rows"}]},
        })
