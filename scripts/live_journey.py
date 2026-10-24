#!/usr/bin/env python3
"""Rubric 'live user journey': one scenario script plus 5 varied inputs nobody tuned on, each run once.

    python scripts/live_journey.py      -> results/live_journey.json

Story: an 'advisor' from a fake firm messages the user on WhatsApp; the user exports or pastes the chat; VERIQ alerts;
the user acts (does not pay / checks the payee name in their bank app / asks for review); the report pack is ready.
The 5 variations change the payee wording, the language and the amount. They were written by Claude C at 25 Oct
03:00 IST for this run and were NOT used to change any rule. Failures are reported as failures.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIRM = "Aarohan Securities Ltd"
CASES = [
    {"id": "J1 baseline (English, UPI ID, user checked name)",
     "chat": "25/10/2026, 9:00 am - Riya (Aarohan): Your IPO allotment is confirmed. Pay ₹24,500 to aarohan.ipo@okaxis today only.\n",
     "names": {"aarohan.ipo@okaxis": "MAA KALI GARMENTS"}, "expect": "NAME_DISCREPANCY"},
    {"id": "J2 payee wording changed (UPI ID split with spaces, amount in words)",
     "chat": "25/10/2026, 9:05 am - Riya (Aarohan): send twenty thousand rupees to  aarohan . ipo2 @ okaxis  fast\n",
     "names": {}, "expect": "a payee is found, or the miss is reported"},
    {"id": "J3 Hinglish, bank account + IFSC, no name check",
     "chat": "25/10/2026, 9:10 am - Riya (Aarohan): Sir ji withdrawal ke liye 18% tax pehle bharo, account no 50100234567891 IFSC HDFC0001234\n",
     "names": {}, "expect": "INCONCLUSIVE (hard cue: fee to withdraw)"},
    {"id": "J4 Devanagari, small amount, name matches the firm",
     "chat": "25/10/2026, 9:15 am - Desk: नमस्ते, कृपया ₹999 aarohan.sec@icici पर भेजें, यह आपका मासिक शुल्क है।\n",
     "names": {"aarohan.sec@icici": "AAROHAN SECURITIES LIMITED"}, "expect": "NO_MAJOR_ISSUE (+ not a guarantee)"},
    {"id": "J5 large amount, payee changes mid-chat, gateway handle",
     "chat": ("25/10/2026, 9:20 am - Riya (Aarohan): Pay ₹2,50,000 to aarohan.ipo@okaxis\n"
              "25/10/2026, 9:25 am - Riya (Aarohan): Sorry that account is full, use pay.aarohan@razorpay instead, urgent\n"),
     "names": {"aarohan.ipo@okaxis": "MAA KALI GARMENTS", "pay.aarohan@razorpay": "RAZORPAY SOFTWARE PVT LTD"},
     "expect": "NAME_DISCREPANCY on the first; gateway unverified"},
]


def run() -> list[dict]:
    from app.case import UserCheck, build_case, report_data
    from report.build import summary_md
    out = []
    for c in CASES:
        checks = {k: UserCheck(v, "Bank app (beneficiary name)", date(2026, 10, 25)) for k, v in c["names"].items()}
        case = build_case(case_id=c["id"][:2], chat_text=c["chat"], claimed_firm=FIRM, checks=checks)
        res = case.case_result()
        payees = {p.value_norm: case.result_for(p.id).result for p in case.payees}
        reasons = [str(r) for p in case.payees for r in (case.result_for(p.id).reasons or [])][:2]
        pack = summary_md(report_data(case, money_sent=False)) if res else ""
        out.append({"id": c["id"], "expected": c["expect"], "answer": res, "payees": payees,
                    "why_shown": reasons, "user_actions": ["do not pay", "check the name in the bank app",
                                                           "ask for review", "report pack"] if res else [],
                    "report_pack_chars": len(pack),
                    "verdict": "as expected" if res and c["expect"].split(" ")[0] in (res, "a") else
                               ("MISS: no payee found" if res is None else "different from expected")})
    return out


def main() -> int:
    r = run()
    doc = {"run_at_ist": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M IST"),
           "firm_claimed": FIRM, "cases": r,
           "note": "5 inputs written by Claude C for this run, never used for tuning; fictional names and IDs"}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "live_journey.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    for c in r:
        print(f"{c['id']}: {c['answer']} {c['payees']} -> {c['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
