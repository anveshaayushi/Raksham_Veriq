#!/usr/bin/env python3
"""Rubric 'responsible AI and handling mistakes': what a GENUINE user flagged by mistake goes through, measured.

    python scripts/mistake_path.py      -> results/mistake_path.json

Drives the real app (streamlit.testing, no browser) through scenario D: a legitimate broker whose bank account is
registered under a short trading name, so VERIQ says NAME_DISCREPANCY (a false alarm). Counts the user's and the
reviewer's clicks, measures the app's own processing time for each step, and records what is kept (the audit trail).
Human reading/thinking time and the reviewer's checking time are NOT included: say so when quoting the number.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run() -> dict:
    from streamlit.testing.v1 import AppTest
    steps = []

    def do(label, who, fn):
        t0 = time.perf_counter()
        fn()
        steps.append({"step": label, "who": who, "app_seconds": round(time.perf_counter() - t0, 3)})

    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=180)
    at.run()
    btn = lambda k: next(b for b in at.button if b.key == k)  # noqa: E731
    do("open the scenario player", "user", lambda: at.radio(key="page_radio").set_value("Scenario player").run())
    do("pick scenario D", "user", lambda: at.radio(key="pl_sid").set_value("D").run())
    do("chat arrives (show all messages)", "user", lambda: btn("pl_all").click().run())
    shown = " ".join(m.value for m in at.markdown)
    first = "NAME_DISCREPANCY" if "NAME_DISCREPANCY" in shown else "?"
    reason = next((m.value for m in at.markdown if m.value.startswith("- `sslcap")), "")
    do("user: 'this is my real broker, ask for review'", "user", lambda: btn("pl_req").click().run())
    do("reviewer: SEBI Check confirms the @valid handle, overturn", "reviewer", lambda: btn("pl_over").click().run())
    done = " ".join(x.value for x in at.success)
    led = at.session_state.pl_ledger
    audit = json.loads(led.audit_json())
    return {"scenario": "D (synthetic): Sahyadri Securities Ltd; bank app shows 'SSL CAPITAL SERVICES'",
            "first_answer": first, "reason_shown": reason, "final": "overturned" if "Overturned" in done else "not cleared",
            "user_clicks_after_alert": sum(s["who"] == "user" for s in steps[3:]),
            "reviewer_clicks": sum(s["who"] == "reviewer" for s in steps),
            "app_processing_seconds_total": round(sum(s["app_seconds"] for s in steps), 2),
            "steps": steps, "recorded": {"audit_actions": [a["action"] for a in audit["audit_trail"]],
                                          "raw_payee_id_in_audit": "sslcap.sec@validicici" in json.dumps(audit["audit_trail"])},
            "not_included": "human reading time and the reviewer's checking time (a person checks SEBI Check)",
            "run_at_ist": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST")}


def main() -> int:
    r = run()
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "mistake_path.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r, indent=1))
    return 0 if r["final"] == "overturned" else 1


if __name__ == "__main__":
    raise SystemExit(main())
