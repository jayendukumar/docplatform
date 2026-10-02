"""Pure reusable-component expansion rules used by document rendering."""
from __future__ import annotations

import json
from typing import Any


class ComponentExpansionError(ValueError):
    """Raised when a component reference cannot be safely expanded."""


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
