"""Rubric 'live user journey' and 'handling mistakes': the scripted runs work and report what they measure."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def test_mistake_path_genuine_user_is_cleared_with_reason_and_audit():
    import mistake_path
    r = mistake_path.run()
    assert r["first_answer"] == "NAME_DISCREPANCY" and r["final"] == "overturned"
    assert "why:" in r["reason_shown"] and r["user_clicks_after_alert"] == 1 and r["reviewer_clicks"] == 1
    assert r["recorded"]["audit_actions"] == ["review requested", "overturned"]
    assert r["recorded"]["raw_payee_id_in_audit"] is False


def test_live_journey_five_variations_reported_including_misses():
    import live_journey
    r = {c["id"][:2]: c for c in live_journey.run()}
    assert len(r) == 5
    assert r["J1"]["answer"] == "NAME_DISCREPANCY" and r["J3"]["answer"] == "INCONCLUSIVE"
    assert r["J4"]["answer"] == "NO_MAJOR_ISSUE"
    assert r["J2"]["verdict"].startswith(("MISS", "as expected"))  # the spaced-out UPI ID: reported either way
