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
    output_stream = sys.stdout
    try:
        # Parser/OCR libraries may print notices to stdout during import. Keep
        # the worker's stdout as a single machine-readable JSON envelope.
        sys.stdout = sys.stderr
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
            from app.ocr_preprocessing import prepare_ocr_input
            raw = base64.b64decode(payload["data_base64"], validate=True)
            from app.ocr_preprocessing import map_ocr_box_to_source
            options = dict(payload.get("preprocessing") or {})
            retry = bool(options.pop("retry", True))
            strategies = [options]
            if retry:
                strategies.extend([{**options, "contrast": True}, {**options, "denoise": True}])
            attempts = []
            selected = {"pages": []}
            selected_score = -1.0
            transforms = []
            failures = []
            for number, strategy in enumerate(strategies, 1):
                try:
                    prepared, transform = prepare_ocr_input(
                        raw, strategy, max_pixels=int(payload.get("max_pixels", 40_000_000)),
                        regions=payload.get("regions"))
                    candidate = run_ocr(prepared, payload["command"], payload["language"],
                                        int(payload["timeout_seconds"]))
                    page_transforms = transform.get("pages", [])
                    scores = []
                    merged_pages: dict[int, dict[str, Any]] = {}
                    for result_index, page in enumerate(candidate["pages"]):
                        source_info = (page_transforms[result_index]
                                       if result_index < len(page_transforms) else None)
                        source_page_number = int((source_info or {}).get("page_number", page["page_number"]))
                        target = merged_pages.setdefault(source_page_number,
                                                         {"page_number": source_page_number, "elements": []})
                        mapped = [{**element,
                                   "id": f"region-{result_index + 1}-{element['id']}"
                                   if payload.get("regions") else element["id"],
                                   "box": map_ocr_box_to_source(element["box"], source_info)}
                                  for element in page["elements"]]
                        target["elements"].extend(mapped)
                        scores.extend(element["confidence"] for element in mapped
                                      if element.get("confidence") is not None)
                    candidate["pages"] = list(merged_pages.values())
                    mean_score = sum(scores) / len(scores) if scores else 0.0
                    attempts.append({"attempt": number, "status": "completed",
                                     "mean_engine_confidence": round(mean_score, 4),
                                     "element_count": sum(len(page["elements"]) for page in candidate["pages"])})
                    transforms.append(transform)
                    if mean_score > selected_score:
                        selected, selected_score = candidate, mean_score
                    # Stop once the engine reports a usable result; low confidence
                    # candidates are retained while alternative preprocessing is tried.
                    if mean_score >= 0.55 or not retry:
                        break
                except Exception as exc:  # noqa: BLE001 - preserve per-attempt diagnostics
                    failures.append({"attempt": number, "error": str(exc)[:300]})
                    attempts.append({"attempt": number, "status": "failed"})
                    if not retry:
                        break
            result = selected
            low_confidence = [{"page_number": page["page_number"], "element_id": element["id"],
                               "confidence": element.get("confidence")}
                              for page in result["pages"] for element in page["elements"]
                              if element.get("confidence") is not None and element["confidence"] < 0.55]
            result["recovery"] = {"attempts": attempts, "failures": failures,
                                  "low_confidence_regions": low_confidence,
                                  "confidence_note": "Engine-reported score; not calibrated correctness."}
            result["preprocessing"] = transforms[-1] if transforms else {
                "applied": False, "settings": options, "pages": []}
        elif kind == "pdf-inspect":
            from app.ingestion import simple_pdf_document
            from app.pdf_classification import classify_pdf_pages
            from app.pdf_physical import extract_pdf_physical
            from app.pdf_validation import PdfValidationStage
            from app.pipeline import PipelineError, ProcessingArtifact, run_pipeline
            raw = base64.b64decode(payload["data_base64"], validate=True)
            artifact = ProcessingArtifact(filename=payload["filename"], media_type="application/pdf", content=raw)
            try:
                validated = run_pipeline(artifact, [PdfValidationStage(max_pages=int(payload["max_pages"]))])
                page_classifications = classify_pdf_pages(raw)
                page_routes = ["scan" if item["classification"] == "scanned" else
                               "mixed" if item["classification"] == "mixed-content" else "digital"
                               for item in page_classifications]
                elements = simple_pdf_document(raw) if payload["route"] != "scan" else {}
                physical_content = extract_pdf_physical(raw, include_characters=bool(
                    payload.get("include_characters", False)))
                from app.pdf_analysis import analyze_pdf_document
                logical_content = analyze_pdf_document(
                    {"pages": validated.metadata.get("pages", [])}, physical_content, raw_pdf=raw)
                result = {"sha256": validated.sha256, "metadata": validated.metadata,
                          "page_classifications": page_classifications,
                          "physical_content": physical_content,
                          "logical_content": logical_content,
                          "page_routes": page_routes,
                          "page_elements": {str(number): values for number, values in elements.items()}}
            except PipelineError as exc:
                result = {"validation_error": {"stage": exc.stage, "code": exc.code,
                                                "message": exc.message}}
        elif kind == "pdf-render":
            from app.pdf_render import render_html_to_pdf
            output, report = render_html_to_pdf(payload["html"], payload["command"],
                                                int(payload["timeout_seconds"]),
                                                int(payload["max_output_bytes"]), payload["metadata"],
                                                payload.get("renderer", "chromium"), payload.get("license_file"))
            result = {"pdf_base64": base64.b64encode(output).decode("ascii"), "report": report}
        else:
            raise ValueError("unsupported worker kind")
        sys.stdout = output_stream
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001 - child must serialize all failures to its parent
        sys.stdout = output_stream
        print(json.dumps({"ok": False, "error": str(exc)[:500]}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
