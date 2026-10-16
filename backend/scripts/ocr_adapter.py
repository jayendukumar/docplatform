"""JSON-lines adapter for locally installed PaddleOCR and Tesseract engines."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _tesseract(path: Path, language: str, binary: str | None) -> dict[str, Any]:
    import pytesseract
    from PIL import Image

    if binary:
        pytesseract.pytesseract.tesseract_cmd = binary
    pages = []
    with Image.open(path) as source:
        for page_number in range(getattr(source, "n_frames", 1)):
            source.seek(page_number)
            image = source.convert("RGB")
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            groups: dict[tuple[int, int, int], list[int]] = {}
            for index, text in enumerate(data["text"]):
                if str(text).strip():
                    key = (int(data["block_num"][index]), int(data["par_num"][index]), int(data["line_num"][index]))
                    groups.setdefault(key, []).append(index)
            elements = []
            for index, word_ids in enumerate(groups.values(), 1):
                x0 = min(int(data["left"][i]) for i in word_ids)
                y0 = min(int(data["top"][i]) for i in word_ids)
                x1 = max(int(data["left"][i]) + int(data["width"][i]) for i in word_ids)
                y1 = max(int(data["top"][i]) + int(data["height"][i]) for i in word_ids)
                scores = [float(data["conf"][i]) for i in word_ids if float(data["conf"][i]) >= 0]
                elements.append({"id": f"tesseract-{page_number + 1}-{index}",
                                 "text": " ".join(str(data["text"][i]).strip() for i in word_ids),
                                 "box": [x0, y0, x1, y1],
                                 "confidence": sum(scores) / len(scores) / 100 if scores else None})
            pages.append({"page_number": page_number + 1, "width": image.width,
                          "height": image.height, "coordinate_space": "pixels", "elements": elements})
    return {"pages": pages}


def _paddle(path: Path, language: str, det_dir: str | None, rec_dir: str | None) -> dict[str, Any]:
    if not det_dir or not rec_dir:
        raise ValueError("PaddleOCR requires explicit local detection and recognition model directories")
    if not Path(det_dir).is_dir() or not Path(rec_dir).is_dir():
        raise ValueError("Configured PaddleOCR model directory is missing")
    from paddleocr import PaddleOCR

    paddle_language = {"eng": "en", "chi-sim": "ch", "chi-tra": "chinese_cht",
                       "jpn": "japan", "kor": "korean"}.get(language.casefold(), language)
    engine = PaddleOCR(lang=paddle_language, device="cpu", text_detection_model_dir=det_dir,
                       text_recognition_model_dir=rec_dir, use_doc_orientation_classify=False,
                       use_doc_unwarping=False, use_textline_orientation=False)
    from PIL import Image
    results = engine.predict(str(path))
    pages = []
    width = height = 0
    with Image.open(path) as source:
        source_sizes = []
        for page_number in range(getattr(source, "n_frames", 1)):
            source.seek(page_number)
            source_sizes.append(source.size)
    for page_index, result in enumerate(results):
        payload = result.json.get("res", {}) if hasattr(result, "json") else {}
        width, height = source_sizes[min(page_index, len(source_sizes) - 1)]
        polygons = payload.get("dt_polys", [])
        texts, scores = payload.get("rec_texts", []), payload.get("rec_scores", [])
        elements = []
        for polygon, text, score in zip(polygons, texts, scores):
            points = [[float(point[0]), float(point[1])] for point in polygon]
            elements.append({"id": f"paddle-{page_index + 1}-{len(elements) + 1}", "text": str(text),
                             "box": [min(p[0] for p in points), min(p[1] for p in points),
                                     max(p[0] for p in points), max(p[1] for p in points)],
                             "confidence": float(score)})
        pages.append({"page_number": page_index + 1, "width": width, "height": height,
                      "coordinate_space": "pixels", "elements": elements})
    return {"pages": pages}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", choices=("tesseract", "paddleocr"))
    parser.add_argument("input")
    parser.add_argument("language")
    parser.add_argument("--tesseract-binary")
    parser.add_argument("--det-model-dir")
    parser.add_argument("--rec-model-dir")
    args = parser.parse_args()
    result = (_tesseract(Path(args.input), args.language, args.tesseract_binary)
              if args.engine == "tesseract" else
              _paddle(Path(args.input), args.language, args.det_model_dir, args.rec_model_dir))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
