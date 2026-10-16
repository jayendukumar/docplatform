"""Optional bounded local image preparation for explicitly configured OCR."""
from __future__ import annotations

import math
from io import BytesIO
from typing import Any


class OcrPreprocessingError(ValueError):
    pass


def validate_preprocessing(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - {
        "deskew", "deskew_angle_degrees", "detect_rotation", "rotation_degrees",
        "denoise", "contrast", "dpi",
    }:
        raise OcrPreprocessingError("OCR preprocessing contains unsupported settings")
    result = {"deskew": bool(value.get("deskew", False)),
              "detect_rotation": bool(value.get("detect_rotation", False)),
              "denoise": bool(value.get("denoise", False)),
              "contrast": bool(value.get("contrast", False)),
              "rotation_degrees": int(value.get("rotation_degrees", 0)),
              "dpi": int(value.get("dpi", 180))}
    if result["rotation_degrees"] not in {0, 90, 180, 270}:
        raise OcrPreprocessingError("rotation_degrees must be 0, 90, 180, or 270")
    if not 72 <= result["dpi"] <= 300:
        raise OcrPreprocessingError("OCR render dpi must be between 72 and 300")
    angle = value.get("deskew_angle_degrees")
    if angle is not None:
        try:
            angle = float(angle)
        except (TypeError, ValueError):
            raise OcrPreprocessingError("deskew_angle_degrees must be numeric") from None
        if not math.isfinite(angle) or abs(angle) > 10:
            raise OcrPreprocessingError("deskew_angle_degrees must be between -10 and 10")
        result["deskew_angle_degrees"] = angle
    return result


def _estimate_skew(image: Any) -> float:
    """Estimate small text-line skew from horizontal projection concentration."""
    from PIL import Image, ImageOps

    gray = ImageOps.grayscale(image)
    sample = gray.copy()
    sample.thumbnail((400, 400))
    threshold = 180
    best_angle, best_score = 0.0, -1.0
    for tenth in range(-50, 51, 5):
        angle = tenth / 10
        rotated = sample.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=255, expand=False)
        width, height = rotated.size
        row_ink = [0] * height
        pixels = rotated.load()
        for y in range(height):
            row_ink[y] = sum(1 for x in range(width) if pixels[x, y] < threshold)
        mean = sum(row_ink) / max(1, len(row_ink))
        score = sum((value - mean) ** 2 for value in row_ink) / max(1, len(row_ink))
        if score > best_score:
            best_angle, best_score = angle, score
    return best_angle


def _process_image(image: Any, settings: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    from PIL import ImageFilter, ImageOps

    detected_rotation = _estimate_skew(image) if settings.get("detect_rotation") else None
    angle = settings.get("deskew_angle_degrees")
    if angle is None and settings.get("deskew"):
        angle = detected_rotation if detected_rotation is not None else _estimate_skew(image)
    angle = float(angle or 0.0)
    right_angle = int(settings.get("rotation_degrees", 0))
    processed = image.convert("RGB")
    if settings.get("contrast"):
        processed = ImageOps.autocontrast(processed.convert("L")).convert("RGB")
    if settings.get("denoise"):
        processed = processed.filter(ImageFilter.MedianFilter(size=3))
    if right_angle:
        processed = processed.rotate(-right_angle, expand=True, fillcolor="white")
    if angle:
        # Keep the same canvas; the affine metadata maps OCR boxes back to source pixels.
        from PIL import Image
        processed = processed.rotate(angle, resample=Image.Resampling.BICUBIC,
                                     expand=False, fillcolor="white")
    return processed, {"detected_skew_degrees": detected_rotation,
                       "deskew_applied_degrees": angle,
                       "rotation_applied_degrees": right_angle,
                       "source_pixel_size": list(image.size),
                       "processed_pixel_size": list(processed.size)}


def prepare_ocr_input(data: bytes, settings: Any, *, max_pixels: int,
                      regions: list[dict[str, Any]] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Return the original bytes or a derived multipage TIFF and mapping metadata."""
    options = validate_preprocessing(settings)
    if (not data.startswith(b"%PDF-") and not options) or not any((options.get("deskew"), options.get("detect_rotation"),
                               options.get("denoise"), options.get("contrast"),
                               options.get("rotation_degrees"))):
        if data.startswith(b"%PDF-"):
            pass  # PDFs still need a local raster render for either OCR adapter.
        else:
            try:
                from PIL import Image
                image = Image.open(BytesIO(data))
                image.load()
                if image.width * image.height > max_pixels:
                    raise OcrPreprocessingError("OCR image exceeds the configured pixel limit")
                return data, {"applied": False, "settings": options, "pages": [{
                    "page_number": 1, "page_width_points": float(image.width),
                    "page_height_points": float(image.height), "render_width_pixels": image.width,
                    "render_height_pixels": image.height, "source_pixel_size": list(image.size),
                    "processed_pixel_size": list(image.size), "deskew_applied_degrees": 0,
                    "rotation_applied_degrees": 0}]}
            except OcrPreprocessingError:
                raise
            except (OSError, ValueError):
                return data, {"applied": False, "settings": options, "pages": []}
    try:
        from PIL import Image
    except ImportError:
        raise OcrPreprocessingError("Pillow is required for requested OCR preprocessing") from None

    pages: list[Any] = []
    transforms: list[dict[str, Any]] = []
    if data.startswith(b"%PDF-"):
        try:
            import pymupdf
            document = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:  # noqa: BLE001
            raise OcrPreprocessingError(f"PDF page rendering is unavailable: {type(exc).__name__}") from None
        try:
            scale = float(options["dpi"]) / 72.0
            total_pixels = 0
            selected = regions or []
            render_jobs = []
            if selected:
                for region in selected:
                    page_number = int(region["page_number"])
                    if page_number < 1 or page_number > len(document):
                        raise OcrPreprocessingError("OCR region references a page outside the PDF")
                    rect = pymupdf.Rect(*region["box"])
                    render_jobs.append((page_number, document[page_number - 1], rect))
            else:
                render_jobs = [(page_number, page, None)
                               for page_number, page in enumerate(document, 1)]
            for page_number, page, clip in render_jobs:
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale),
                                         clip=clip, alpha=False)
                total_pixels += pixmap.width * pixmap.height
                if pixmap.width * pixmap.height > max_pixels or total_pixels > max_pixels:
                    raise OcrPreprocessingError("OCR rendered pages exceed the configured pixel limit")
                mode = "RGB" if pixmap.n >= 3 else "L"
                image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
                processed, transform = _process_image(image, options)
                width_points = float(clip.width if clip else page.rect.width)
                height_points = float(clip.height if clip else page.rect.height)
                transforms.append({"page_number": page_number,
                                   "page_width_points": width_points,
                                   "page_height_points": height_points,
                                   "page_origin_points": ([float(clip.x0), float(clip.y0)] if clip else [0, 0]),
                                   "render_width_pixels": pixmap.width,
                                   "render_height_pixels": pixmap.height,
                                   **transform})
                pages.append(processed)
        finally:
            document.close()
    else:
        try:
            image = Image.open(BytesIO(data))
            image.load()
        except Exception as exc:  # noqa: BLE001
            raise OcrPreprocessingError(f"image preprocessing could not decode input: {type(exc).__name__}") from None
        if image.width * image.height > max_pixels:
            raise OcrPreprocessingError("OCR image exceeds the configured pixel limit")
        processed, transform = _process_image(image, options)
        transforms.append({"page_number": 1, "page_width_points": float(image.width),
                           "page_height_points": float(image.height),
                           "render_width_pixels": image.width, "render_height_pixels": image.height,
                           **transform})
        pages.append(processed)
    if not pages:
        raise OcrPreprocessingError("OCR preprocessing produced no pages")
    output = BytesIO()
    pages[0].save(output, format="TIFF", save_all=True, append_images=pages[1:],
                  compression="tiff_deflate")
    result = output.getvalue()
    if len(result) > 20_000_000:
        raise OcrPreprocessingError("preprocessed OCR document exceeds the 20 MB limit")
    return result, {"applied": True, "settings": options, "pages": transforms}


def map_ocr_box_to_source(box: list[float], page_info: dict[str, Any] | None) -> list[float]:
    """Map an OCR pixel rectangle to original top-left page points/pixels."""
    if not page_info:
        return [round(float(value), 3) for value in box]
    width = float(page_info.get("page_width_points") or page_info.get("page_width_pixels") or 0)
    height = float(page_info.get("page_height_points") or page_info.get("page_height_pixels") or 0)
    render_width = float(page_info.get("render_width_pixels") or width or 1)
    render_height = float(page_info.get("render_height_pixels") or height or 1)
    angle = math.radians(float(page_info.get("deskew_applied_degrees") or 0))
    right_angle = math.radians(float(page_info.get("rotation_applied_degrees") or 0))
    cx, cy = render_width / 2, render_height / 2
    corners = [(float(box[0]), float(box[1])), (float(box[2]), float(box[1])),
               (float(box[0]), float(box[3])), (float(box[2]), float(box[3]))]
    mapped: list[tuple[float, float]] = []
    # PIL applies clockwise right-angle rotation then counter-clockwise deskew.
    for x, y in corners:
        x -= cx
        y -= cy
        if angle:
            x, y = (x * math.cos(angle) + y * math.sin(angle),
                    -x * math.sin(angle) + y * math.cos(angle))
        if right_angle:
            x, y = (x * math.cos(right_angle) + y * math.sin(right_angle),
                    -x * math.sin(right_angle) + y * math.cos(right_angle))
        mapped.append((x + cx, y + cy))
    sx = width / render_width if render_width else 1.0
    sy = height / render_height if render_height else 1.0
    xs = [min(width, max(0.0, point[0] * sx)) for point in mapped]
    ys = [min(height, max(0.0, point[1] * sy)) for point in mapped]
    origin = page_info.get("page_origin_points", [0, 0])
    return [round(min(xs) + float(origin[0]), 3), round(min(ys) + float(origin[1]), 3),
            round(max(xs) + float(origin[0]), 3), round(max(ys) + float(origin[1]), 3)]
