import pytest

from app.layout import LayoutEngineError, map_layout_elements, map_layout_output


def test_layout_mapper_preserves_roles_order_and_boxes():
    elements, layout = map_layout_elements([
        {"id": "h1", "text": "# Invoice", "box": [1, 2, 90, 20]},
        {"id": "row", "text": "Widget | 2 | 4.00", "box": [1, 24, 120, 40]},
    ])
    assert [item["role"] for item in elements] == ["heading", "table_row"]
    assert layout["reading_order"] == ["h1", "row"]
    assert elements[1]["box"] == [1, 24, 120, 40]


def test_layout_output_maps_normalized_engine_pages():
    mapped = map_layout_output({"schema_version": 1, "pages": [{
        "page_number": 2, "width": 600, "height": 800,
        "elements": [{"id": "e2", "type": "text", "text": "Body", "box": [10, 20, 80, 40]}],
    }]})
    assert mapped["pages"][0]["page_number"] == 2
    assert mapped["pages"][0]["layout"]["reading_order"] == ["e2"]


@pytest.mark.parametrize("bad", [
    {"schema_version": 2, "pages": []},
    {"schema_version": 1, "pages": [{"elements": [{"id": "x", "box": [1, 2, 1, 3]}]}]},
    {"schema_version": 1, "pages": [{"elements": [{"id": "x", "box": [1, 2, 3, 4]},
                                                       {"id": "x", "box": [1, 2, 3, 4]}]}]},
])
def test_layout_mapper_rejects_incompatible_engine_output(bad):
    with pytest.raises(LayoutEngineError):
        map_layout_output(bad)
