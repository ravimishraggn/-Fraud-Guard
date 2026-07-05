"""OCR service — PaddleOCR with image quality gate and PDF support.

Output contract:
{
  "text": "full extracted text",
  "words": [{"text": str, "confidence": float, "bbox": {...}}],
  "overall_confidence": float,
  "engine_used": "paddleocr",
  "pages": int
}
On unusable input: {"error": "quality_too_low", "message": "..."}
"""
import io
import logging
from typing import Any, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

MIN_DIMENSION_PX = 300          # roughly 100 DPI equivalent for an A6 receipt
BLUR_THRESHOLD = 40.0           # Laplacian variance below this = too blurry

_paddle_ocr = None
_paddle_failed = False


def _get_paddle():
    """Lazy-load PaddleOCR once per worker. Returns None if unavailable."""
    global _paddle_ocr, _paddle_failed
    if _paddle_failed:
        return None
    if _paddle_ocr is None:
        try:
            from paddleocr import PaddleOCR

            _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        except Exception:
            logger.exception("PaddleOCR unavailable — OCR will return empty results")
            _paddle_failed = True
            return None
    return _paddle_ocr


def _quality_check(image: Image.Image) -> Optional[str]:
    """Return an error message if the image is unusable, else None."""
    if image.width < MIN_DIMENSION_PX or image.height < MIN_DIMENSION_PX:
        return (
            f"Image resolution too low ({image.width}x{image.height}). "
            "Please upload a photo of at least 300px on each side."
        )
    try:
        import cv2

        gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        if variance < BLUR_THRESHOLD:
            return "Image is too blurry to read. Please retake the photo in good light."
    except Exception:
        # If OpenCV blur detection fails, don't block the pipeline.
        logger.warning("Blur detection skipped", exc_info=True)
    return None


def _preprocess(image: Image.Image) -> Image.Image:
    """Light preprocessing: grayscale conversion + upscale small images."""
    img = image.convert("RGB")
    if max(img.width, img.height) < 1200:
        scale = 1200 / max(img.width, img.height)
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    return img


def _ocr_image(image: Image.Image) -> dict[str, Any]:
    ocr = _get_paddle()
    if ocr is None:
        return {"text": "", "words": [], "overall_confidence": 0.0}
    result = ocr.ocr(np.array(image), cls=True)
    words: list[dict] = []
    lines: list[str] = []
    confidences: list[float] = []
    for page in result or []:
        for entry in page or []:
            bbox_pts, (text, conf) = entry
            xs = [p[0] for p in bbox_pts]
            ys = [p[1] for p in bbox_pts]
            words.append(
                {
                    "text": text,
                    "confidence": round(float(conf), 4),
                    "bbox": {
                        "x": min(xs),
                        "y": min(ys),
                        "w": max(xs) - min(xs),
                        "h": max(ys) - min(ys),
                    },
                }
            )
            lines.append(text)
            confidences.append(float(conf))
    return {
        "text": "\n".join(lines),
        "words": words,
        "overall_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
    }


def run_ocr(data: bytes, mime_type: str) -> dict[str, Any]:
    """OCR a file (image or PDF). Never raises — returns an error dict instead."""
    try:
        if mime_type == "application/pdf":
            from pdf2image import convert_from_bytes

            pages = convert_from_bytes(data, dpi=200)
            if not pages:
                return {"error": "quality_too_low", "message": "PDF has no readable pages."}
            all_text, all_words, confs = [], [], []
            for page_num, page_img in enumerate(pages, start=1):
                err = _quality_check(page_img)
                if err and page_num == 1:
                    return {"error": "quality_too_low", "message": err}
                page_result = _ocr_image(_preprocess(page_img))
                for w in page_result["words"]:
                    w["page"] = page_num
                all_text.append(page_result["text"])
                all_words.extend(page_result["words"])
                if page_result["overall_confidence"]:
                    confs.append(page_result["overall_confidence"])
            return {
                "text": "\n\n".join(all_text),
                "words": all_words,
                "overall_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
                "engine_used": "paddleocr",
                "pages": len(pages),
            }

        image = Image.open(io.BytesIO(data))
        err = _quality_check(image)
        if err:
            return {"error": "quality_too_low", "message": err}
        result = _ocr_image(_preprocess(image))
        result["engine_used"] = "paddleocr"
        result["pages"] = 1
        return result
    except Exception as exc:
        logger.exception("OCR failed")
        return {"error": "ocr_failed", "message": f"Could not read this file: {exc}"}
