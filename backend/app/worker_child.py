"""Child-process entry point; never receives database or storage credentials."""
from __future__ import annotations

import base64
import json
import socket
import sys
from typing import Any


def _deny_network(*args: Any, **kwargs: Any):
    raise OSError("network access is disabled in document workers")


def _apply_limits(cpu_seconds: int, memory_bytes: int | None) -> None:
    try:
        import resource
    except ImportError:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    if memory_bytes is None:
        # Node's WebAssembly runtime rejects a finite inherited RLIMIT_AS,
        # including large limits. Chromium remains isolated and bounded by
        # the worker/container memory ceiling plus wall/output limits.
        resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    else:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))


def main() -> int:
    try:
        request = json.load(sys.stdin)
        kind = request["kind"]
        payload = request["payload"]
        _apply_limits(int(sys.argv[1]), None if kind == "pdf-render" else int(sys.argv[2]))
        socket.socket.connect = _deny_network
        socket.socket.connect_ex = _deny_network
        socket.create_connection = _deny_network
        socket.socket.sendto = _deny_network
        if hasattr(socket.socket, "sendmsg"):
            socket.socket.sendmsg = _deny_network
        if kind == "render":
            from app.rendering import render_definition
            result = render_definition(payload["definition"], payload.get("data"),
                                       payload.get("locale"), payload.get("missing_policy"))
        elif kind == "extraction":
            from app.engines import extract_with_engine
            result = extract_with_engine(payload.get("engine_id", "local-label-extractor"),
                                         payload["page_model"], payload["schema"], payload.get("locale", "en"))
        elif kind == "ocr":
            from app.ocr import run_ocr
            raw = base64.b64decode(payload["data_base64"], validate=True)
            result = run_ocr(raw, payload["command"], payload["language"], int(payload["timeout_seconds"]))
        elif kind == "pdf-render":
            from app.pdf_render import render_html_to_pdf
            output, report = render_html_to_pdf(payload["html"], payload["command"],
                                                int(payload["timeout_seconds"]),
                                                int(payload["max_output_bytes"]), payload["metadata"],
                                                payload.get("renderer", "chromium"), payload.get("license_file"))
            result = {"pdf_base64": base64.b64encode(output).decode("ascii"), "report": report}
        else:
            raise ValueError("unsupported worker kind")
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001 - child must serialize all failures to its parent
        print(json.dumps({"ok": False, "error": str(exc)[:500]}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
