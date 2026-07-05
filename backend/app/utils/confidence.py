"""Confidence score helpers. All scores are clamped to [0.0, 1.0]."""
from typing import Optional


def clamp_confidence(value: Optional[float]) -> float:
    """Normalise any confidence input into the valid 0.0–1.0 range."""
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    # Handle percentages passed as 0-100
    if v > 1.0 and v <= 100.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))


def combine_confidences(ocr_conf: Optional[float], llm_conf: Optional[float]) -> float:
    """Blend OCR and LLM confidence: weighted toward the LLM judgement."""
    ocr = clamp_confidence(ocr_conf)
    llm = clamp_confidence(llm_conf)
    if ocr == 0.0:
        return llm
    if llm == 0.0:
        return ocr
    return round(0.4 * ocr + 0.6 * llm, 4)
