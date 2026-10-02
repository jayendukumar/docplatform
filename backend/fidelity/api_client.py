"""Minimal client for the platform's public HTTP API (E16).

The harness reaches the application only through these routes, so a
reconstruction can use nothing a user of the editor and API could not.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 180


class ApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None) -> None:
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base URL must be an http(s) URL")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        headers = {"accept": "application/json"}
        body = None
        if payload is not None:
            headers["content-type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        if self.api_key:
            headers["x-api-key"] = self.api_key
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def capabilities(self) -> dict[str, Any]:
        return self._request("GET", "/api/editor/capabilities")

    def save_draft(self, template_id: str, definition: dict[str, Any], *, summary: str) -> dict[str, Any]:
        """Create the template, or add a draft version if the id already exists (the editor's save path)."""
        try:
            return self._request("POST", "/api/templates", {"id": template_id, "name": definition["name"],
                                                             "folder": "E16 fidelity", "tags": ["e16"],
                                                             "definition": definition})
        except urllib.error.HTTPError as error:
            if error.code != 409:
                raise
        return self._request("POST", f"/api/templates/{urllib.parse.quote(template_id, safe='')}/versions",
                             {"definition": definition, "change_summary": summary})

    def render_pdf(self, template_id: str, *, draft: bool = False, data: dict[str, Any] | None = None,
                   locale: str | None = None) -> tuple[bytes, dict[str, Any]]:
        """Render through the normal PDF route without any locked source background."""
        payload: dict[str, Any] = {"draft": draft, "comparison_mode": "editable-only"}
        if data is not None:
            payload["data"] = data
        if locale:
            payload["locale"] = locale
        result = self._request("POST", f"/api/templates/{urllib.parse.quote(template_id, safe='')}/render-pdf", payload)
        return base64.b64decode(result["document_base64"], validate=True), result.get("report", {})
