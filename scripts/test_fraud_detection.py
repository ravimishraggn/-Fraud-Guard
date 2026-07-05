"""Run the fraud engine against synthetic samples and print results.

Usage (inside backend container):
    docker compose exec backend python scripts/test_fraud_detection.py
"""
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app.services.fraud_engine import FraudEngine  # noqa: E402
from app.utils.validators import is_valid_gstin_format, words_to_number  # noqa: E402

engine = FraudEngine()
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")


print("— GSTIN format validation —")
check("valid GSTIN accepted", is_valid_gstin_format("27AAPFU0939F1ZV"))
check("short GSTIN rejected", not is_valid_gstin_format("27AAPFU0939F1Z"))
check("garbage rejected", not is_valid_gstin_format("INVALID123GST99"))

print("— Amount in words parser —")
check("47,500", words_to_number("Forty Seven Thousand Five Hundred Rupees Only") == 47500)
check("41,500", words_to_number("Forty One Thousand Five Hundred Only") == 41500)
check("2.45 lakh", words_to_number("Two Lakh Forty Five Thousand Rupees Only") == 245000)
check("1 crore", words_to_number("One Crore Rupees Only") == 10000000)
check("unparseable → None", words_to_number("asdf qwerty") is None)

print("— Amount/words mismatch check —")
flags = engine.check_amount_words_mismatch(
    None,
    {"amount_numeric": "47500", "amount_in_words": "Forty One Thousand Five Hundred Only"},
    None,
    None,
)
check("mismatch flagged as critical", len(flags) == 1 and flags[0]["severity"] == "critical")
flags = engine.check_amount_words_mismatch(
    None,
    {"amount_numeric": "47500", "amount_in_words": "Forty Seven Thousand Five Hundred Only"},
    None,
    None,
)
check("matching amount not flagged", len(flags) == 0)

print("— Future date check —")
future = (datetime.now() + timedelta(days=40)).strftime("%Y-%m-%d")
flags = engine.check_future_date(None, {"invoice_date": future}, None, None)
check("40 days ahead → critical", len(flags) == 1 and flags[0]["severity"] == "critical")
near_future = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
flags = engine.check_future_date(None, {"invoice_date": near_future}, None, None)
check("5 days ahead → high", len(flags) == 1 and flags[0]["severity"] == "high")
old = (datetime.now() - timedelta(days=900)).strftime("%Y-%m-%d")
flags = engine.check_future_date(None, {"invoice_date": old}, None, None)
check("900 days old → medium (stale)", len(flags) == 1 and flags[0]["severity"] == "medium")
today = datetime.now().strftime("%Y-%m-%d")
flags = engine.check_future_date(None, {"invoice_date": today}, None, None)
check("today → clean", len(flags) == 0)

print("— Risk scoring —")
score, level = engine.calculate_risk_score([])
check("no flags → clean", score == 0 and level == "clean")
score, level = engine.calculate_risk_score([{"severity": "critical"}, {"severity": "critical"}])
check("2 critical → 80/high", score == 80 and level == "high")
score, level = engine.calculate_risk_score([{"severity": "low"}])
check("1 low → 5/clean", score == 5 and level == "clean")
score, level = engine.calculate_risk_score(
    [{"severity": "critical"}] * 4 + [{"severity": "high"}] * 5
)
check("caps applied, max 100", score == 100)

print(f"\n{passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
