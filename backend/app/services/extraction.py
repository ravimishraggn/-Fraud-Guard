"""AI extraction service — GPT-4o-mini structured field extraction.

Falls back to a regex-based heuristic extractor when no OpenAI key is
configured, so the local demo works end-to-end without external calls.
"""
import json
import logging
import re
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are a financial document analyser specialised in Indian business documents.
Extract the following fields from the OCR text provided.
Return ONLY valid JSON. No explanation. No markdown.
Required fields to extract (return null if not found):
{
  "document_type": "invoice|receipt|purchase_order|delivery_challan|unknown",
  "vendor_name": "string or null",
  "vendor_gstin": "string or null",
  "vendor_pan": "string or null",
  "vendor_bank_account": "string or null",
  "vendor_bank_ifsc": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "amount_numeric": "number or null",
  "amount_in_words": "string or null",
  "tax_amount": "number or null",
  "tax_rate": "number or null",
  "po_reference": "string or null",
  "payment_terms": "string or null",
  "confidence_scores": {
    "vendor_name": 0.0-1.0,
    "invoice_number": 0.0-1.0,
    "amount_numeric": 0.0-1.0,
    "vendor_gstin": 0.0-1.0
  }
}
Important rules:
- For amounts: extract the FINAL total amount payable
- For GSTIN: must be exactly 15 characters if present
- For dates: convert all formats to YYYY-MM-DD
- If a field has low confidence, still extract it but set confidence < 0.7
- Never guess or hallucinate — return null if genuinely not present
"""

EXPECTED_FIELDS = (
    "document_type", "vendor_name", "vendor_gstin", "vendor_pan",
    "vendor_bank_account", "vendor_bank_ifsc", "invoice_number",
    "invoice_date", "due_date", "amount_numeric", "amount_in_words",
    "tax_amount", "tax_rate", "po_reference", "payment_terms",
)


def _heuristic_extract(ocr_text: str) -> dict[str, Any]:
    """Regex fallback when the LLM is unavailable. Low confidence by design."""
    text = ocr_text or ""
    result: dict[str, Any] = {f: None for f in EXPECTED_FIELDS}
    result["document_type"] = "invoice" if re.search(r"\binvoice\b", text, re.I) else "unknown"

    gstin = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", text)
    if gstin:
        result["vendor_gstin"] = gstin.group(0)
    pan = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text)
    if pan:
        result["vendor_pan"] = pan.group(0)
    inv = re.search(r"invoice\s*(?:no|number|#)[:.\s]*([A-Z0-9/-]+)", text, re.I)
    if inv:
        result["invoice_number"] = inv.group(1)
    date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if date:
        result["invoice_date"] = date.group(1)
    amount = re.search(r"(?:total|amount payable|grand total)[:.\s₹Rs]*([\d,]+(?:\.\d{1,2})?)", text, re.I)
    if amount:
        try:
            result["amount_numeric"] = float(amount.group(1).replace(",", ""))
        except ValueError:
            pass
    words = re.search(r"(?:rupees|amount in words)[:.\s]*([A-Za-z\s-]+?)(?:only|\n|$)", text, re.I)
    if words:
        result["amount_in_words"] = words.group(1).strip()

    result["confidence_scores"] = {
        "vendor_name": 0.3,
        "invoice_number": 0.5 if result["invoice_number"] else 0.0,
        "amount_numeric": 0.5 if result["amount_numeric"] else 0.0,
        "vendor_gstin": 0.6 if result["vendor_gstin"] else 0.0,
    }
    result["_extraction_engine"] = "heuristic"
    return result


def extract_fields(ocr_text: str) -> dict[str, Any]:
    """Extract structured invoice fields from OCR text. Never raises."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — using heuristic extraction")
        return _heuristic_extract(ocr_text)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": ocr_text[:24000]},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        # Guarantee every expected key exists
        for field in EXPECTED_FIELDS:
            data.setdefault(field, None)
        data.setdefault("confidence_scores", {})
        data["_extraction_engine"] = "gpt-4o-mini"
        return data
    except Exception:
        logger.exception("LLM extraction failed — falling back to heuristics")
        return _heuristic_extract(ocr_text)
