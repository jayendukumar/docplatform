"""Pure reusable-component expansion rules used by document rendering."""
from __future__ import annotations

import json
from typing import Any


class ComponentExpansionError(ValueError):
    """Raised when a component reference cannot be safely expanded."""


class ComponentDefinitionError(ValueError):
    """Raised when a saved component is not a bounded declarative block tree."""


ALLOWED_COMPONENT_BLOCKS = {
    "text", "rich_text", "table", "loop", "if", "image", "code", "chart", "toc",
    "component", "shape", "columns", "column_break", "columns_end",
}
MAX_COMPONENT_BLOCKS = 100
MAX_COMPONENT_DEPTH = 8


def validate_component_definition(definition: dict[str, Any]) -> None:
    """Validate the safe subset accepted by the component-library API."""
    if not isinstance(definition, dict) or not isinstance(definition.get("blocks"), list):
        raise ComponentDefinitionError("definition.blocks must be an array")
    seen = 0

    def visit(blocks: Any, depth: int) -> None:
        nonlocal seen
        if depth > MAX_COMPONENT_DEPTH:
            raise ComponentDefinitionError("Component nesting is too deep")
        if not isinstance(blocks, list):
            raise ComponentDefinitionError("Nested component blocks must be arrays")
        for block in blocks:
            if not isinstance(block, dict):
                raise ComponentDefinitionError("Component blocks must be objects")
            kind = block.get("type", "text")
            if kind not in ALLOWED_COMPONENT_BLOCKS:
                raise ComponentDefinitionError(f"Unsupported component block type: {kind}")
            seen += 1
            if seen > MAX_COMPONENT_BLOCKS:
                raise ComponentDefinitionError("Component contains too many blocks")
            if kind == "component" and (not isinstance(block.get("component_id"), str) or not block["component_id"]):
                raise ComponentDefinitionError("Nested component references require component_id")
            for key in ("blocks", "then", "else"):
                if key in block:
                    visit(block[key], depth + 1)

    visit(definition["blocks"], 0)


def expand_definition(definition: dict[str, Any], registry: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return a deep-copied definition with component references expanded.

    Component blocks remain references in stored templates. Expansion happens at
    render time so every template using a component observes its latest version.
    The stack is per branch, which permits repeated sibling references while
    rejecting only recursive component cycles.
    """
    result = json.loads(json.dumps(definition, ensure_ascii=False))

    def expand(blocks: Any, stack: tuple[str, ...] = ()) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for block in blocks if isinstance(blocks, list) else []:
            if isinstance(block, dict) and block.get("type") == "component":
                component_id = block.get("component_id")
                if not isinstance(component_id, str) or not component_id:
                    raise ComponentExpansionError("Reusable component reference is missing an id")
                if component_id in stack:
                    raise ComponentExpansionError("Reusable component cycle detected")
                component = registry.get(component_id)
                if component is None:
                    raise ComponentExpansionError(f"Reusable component not found: {component_id}")
                output.extend(expand(component.get("blocks", []), (*stack, component_id)))
                continue
            copied = dict(block)
            for key in ("blocks", "then", "else"):
                if isinstance(copied.get(key), list):
                    copied[key] = expand(copied[key], stack)
            output.append(copied)
        return output

    result["blocks"] = expand(result.get("blocks", []))
    page = result.get("page")
    if isinstance(page, dict):
        for slot in ("header", "footer"):
            component_id = page.get(f"{slot}_component_id")
            if not component_id:
                continue
            if not isinstance(component_id, str):
                raise ComponentExpansionError(f"Page {slot} component reference is invalid")
            if component_id not in registry:
                raise ComponentExpansionError(f"Reusable component not found: {component_id}")
            component_blocks = expand(registry[component_id].get("blocks", []), (component_id,))
            values: list[str] = []
            for block in component_blocks:
                if block.get("type", "text") != "text":
                    raise ComponentExpansionError(f"Page {slot} components may contain text blocks only")
                values.append(str(block.get("text", "")))
            page[slot] = "\n".join(values)
    return result
