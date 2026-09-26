"""Export or import portable template bundles as plain repository files."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from urllib.error import HTTPError
from pathlib import Path
from zipfile import ZipFile


TEMPLATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def normalize_template_ids(values: list[str]) -> list[str]:
    """Split repeated/comma-separated IDs and reject unsafe local path names."""
    result: list[str] = []
    for value in values:
        for candidate in value.split(","):
            template_id = candidate.strip()
            if not template_id or not TEMPLATE_ID.fullmatch(template_id):
                raise ValueError(f"invalid template id: {template_id or '<empty>'}")
            if template_id not in result:
                result.append(template_id)
    return result


def request_json(url: str, *, data: bytes | None = None, method: str = "GET",
                 api_key: str | None = None) -> dict:
    headers = {"content-type": "application/json"} if data else {}
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(url, data=data,
                                     headers=headers,
                                     method=method)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def push_definition(base_url: str, template_id: str, definition: dict, api_key: str | None = None) -> str:
    try:
        request_json(f"{base_url}/api/templates/{template_id}", api_key=api_key)
    except HTTPError as error:
        if error.code != 404:
            raise
        body = json.dumps({"id": template_id, "name": definition.get("name", template_id),
                           "definition": definition}).encode("utf-8")
        result = request_json(f"{base_url}/api/templates", data=body, method="POST", api_key=api_key)
        return str(result.get("id", template_id))
    result = request_json(f"{base_url}/api/templates/{template_id}/versions",
                          data=json.dumps({"definition": definition,
                                           "change_summary": "Repository sync"}).encode("utf-8"),
                          method="POST", api_key=api_key)
    return str(result.get("id", template_id))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["pull", "push"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default=os.environ.get("DOCPLATFORM_SYNC_API_KEY"))
    parser.add_argument("--template-id", action="append", required=True)
    args = parser.parse_args()
    try:
        template_ids = normalize_template_ids(args.template_id)
    except ValueError as error:
        parser.error(str(error))
    args.directory.mkdir(parents=True, exist_ok=True)
    for template_id in template_ids:
        if args.action == "pull":
            request = urllib.request.Request(f"{args.base_url}/api/templates/{template_id}/export",
                                             headers={"x-api-key": args.api_key} if args.api_key else {})
            with urllib.request.urlopen(request) as response:
                bundle = args.directory / f"{template_id}.zip"
                bundle.write_bytes(response.read())
            with ZipFile(bundle) as archive:
                (args.directory / f"{template_id}.json").write_text(
                    archive.read("definition.json").decode("utf-8"), encoding="utf-8")
        else:
            definition = json.loads((args.directory / f"{template_id}.json").read_text(encoding="utf-8"))
            push_definition(args.base_url, template_id, definition, args.api_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
