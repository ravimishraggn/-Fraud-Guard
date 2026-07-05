"""Format validators for Indian tax identifiers and amount-in-words parsing."""
import re
from typing import Optional

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def is_valid_gstin_format(gstin: Optional[str]) -> bool:
    if not gstin:
        return False
    return bool(GSTIN_REGEX.match(gstin.strip().upper()))


def is_valid_pan_format(pan: Optional[str]) -> bool:
    if not pan:
        return False
    return bool(PAN_REGEX.match(pan.strip().upper()))


def is_valid_ifsc_format(ifsc: Optional[str]) -> bool:
    if not ifsc:
        return False
    return bool(IFSC_REGEX.match(ifsc.strip().upper()))


# ---------------------------------------------------------------------------
# Amount-in-words → number, with Indian numbering (lakh / crore) support.
# ---------------------------------------------------------------------------
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "million": 1_000_000,
    "crore": 10_000_000, "crores": 10_000_000,
    "billion": 1_000_000_000,
}
_NOISE = {"rupees", "rupee", "rs", "inr", "only", "and", "paise", "paisa", "rs."}


def words_to_number(text: Optional[str]) -> Optional[int]:
    """Parse an amount written in words into an integer (rupees).

    Supports Indian scales (lakh, crore). Returns None if unparseable.
    """
    if not text:
        return None
    words = re.split(r"[\s,-]+", text.strip().lower())
    total = 0
    current = 0
    matched_any = False
    for word in words:
        w = word.strip(".")
        if not w or w in _NOISE:
            continue
        if w in _UNITS:
            current += _UNITS[w]
            matched_any = True
        elif w in _TENS:
            current += _TENS[w]
            matched_any = True
        elif w == "hundred":
            current = (current or 1) * 100
            matched_any = True
        elif w in _SCALES:
            total += (current or 1) * _SCALES[w]
            current = 0
            matched_any = True
        elif w.isdigit():
            current += int(w)
            matched_any = True
        # Unknown words are ignored (OCR noise tolerance)
    result = total + current
    return result if matched_any else None
