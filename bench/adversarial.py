"""Red-team set (FINALE, Claude C): attacks a scammer would try, each run through the real engine.

    python -m bench.adversarial      -> bench/results_adversarial.json + a Markdown table on stdout

Every case is synthetic and written by us, knowing our defences, so a pass shows the defence works on that attack;
it is not an accuracy number. KNOWN GAPS are included on purpose: they are expected to fail and are reported as such.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRM = "Navyug Broking Pvt Ltd"
B_CHAT = ("15/10/2026, 11:00 am - Sneha: Hello Ankit, this is Sneha from Navyug Broking Pvt Ltd. SEBI reg no INZ000DEMO01.\n"
          "15/10/2026, 11:06 am - Sneha: Add funds on UPI: navyug.brk@validhdfc\n")


def _case(chat, typed=None, images=None, transcripts=None):
    from app.case import UserCheck, build_case
    from extract import extract as _x, payees as _p
    from parsing import parse_chat
    checks = {}
    if typed is not None:
        pays = _p(_x(parse_chat(chat), "adv")[0])
        checks = {p.value_norm: UserCheck(typed, "UPI app (payee name before paying)", date(2026, 10, 24)) for p in pays}
    return build_case(case_id="adv", chat_text=chat, claimed_firm=FIRM, checks=checks, images=images,
                      transcripts=transcripts)


def _cue(text):
    from extract import extract
    from parsing import parse_chat
    return {c.type for c in extract(parse_chat("15/10/2026, 11:00 am - X: " + text + "\n"), "adv")[1]}


def _qr(text):
    import cv2
    img = cv2.QRCodeEncoder.create().encode(text)
    img = cv2.copyMakeBorder(cv2.resize(img, (300, 300), interpolation=cv2.INTER_NEAREST), 30, 30, 30, 30,
                             cv2.BORDER_CONSTANT, value=255)
    return cv2.imencode(".png", img)[1].tobytes()


def run() -> list[dict]:
    rows = []

    def add(group, attack, expected, got, gap=False):
        rows.append({"group": group, "attack": attack, "expected": expected, "got": got,
                     "pass": expected == got, "known_gap": gap})

    # 1. Look-alike / shell payee names (should NOT pass as the firm)
    for typed in ["NAVYUG ONLINE TRADERS", "Navyug Broking Services", "NAVYUG CAPITAL MARKETS", "NAVYUG PAYMENTS",
                  "NAVYUG BROKING SOLUTIONS", "NAVYUG TECH SERVICES"]:
        add("look-alike payee name", typed, "HUMAN_REVIEW", _case(B_CHAT, typed).case_result())
    add("look-alike payee name", "identical name on a mule account (NAVYUG BROKING PVT LTD)", "not NO_MAJOR_ISSUE",
        "NO_MAJOR_ISSUE" if _case(B_CHAT, "NAVYUG BROKING PVT LTD").case_result() == "NO_MAJOR_ISSUE" else "not NO_MAJOR_ISSUE",
        gap=True)
    # genuine variants must still match (false-review check)
    for typed in ["NAVYUG BROKING PRIVATE LIMITED", "NAVYUG BROKING LTD", "M/S NAVYUG BROKING PVT LTD", "Navyug Broking"]:
        add("genuine name variant", typed, "NO_MAJOR_ISSUE", _case(B_CHAT, typed).case_result())
    # unrelated names on the payee (classic mule)
    for typed in ["SHREE GANESH TRADERS", "BALAJI GARMENTS", "RK MOBILE POINT"]:
        add("unrelated payee name", typed, "NAME_DISCREPANCY", _case(B_CHAT, typed).case_result())
    add("unrelated payee name", "KRISHNA DAIRY FARM (contains a given name; known gap until the Q2 shop-word fix)",
        "NAME_DISCREPANCY", _case(B_CHAT, "KRISHNA DAIRY FARM").case_result())

    # 2. Obfuscated / reworded pressure phrases
    for text, cue in [("gu@r@nteed 3x returns", "guaranteed_return"), ("100% guaranteed profit", "guaranteed_return"),
                      ("P.a.y 18% t@x to withdraw", "fee_to_withdraw"), ("pay unfreeze account fee", "fee_to_withdraw"),
                      ("u_r_g_e_n_t", "urgency"), ("send in 5 mins", "urgency"), ("no loss pakka double", "guaranteed_return"),
                      ("sure-shot gain", "guaranteed_return"), ("slot cancel ho jayega", "urgency"),
                      ("share the OTP you got", "otp_pin_request"), ("install AnyDesk", "remote_access")]:
        add("obfuscated pressure phrase", text, cue, cue if cue in _cue(text) else "missed")
    for text, cue in [("your chance closes soon, act fast", "urgency"), ("profit is fixed, you cannot lose", "guaranteed_return")]:
        add("obfuscated pressure phrase", text + " (reworded, no keyword)", cue, cue if cue in _cue(text) else "missed", gap=True)
    for text in ["Please confirm the payee name on your app before paying.", "Onboarding fee ₹10,000",
                 "Markets are volatile; returns are not guaranteed.", "Thanks, received."]:
        hard = {"fee_to_withdraw", "guaranteed_return", "otp_pin_request", "remote_access", "secrecy"} & _cue(text)
        add("benign sentence (false cue check)", text, "no hard cue", "no hard cue" if not hard else ",".join(sorted(hard)),
            gap=False)

    # 3. Payee hidden in a QR image
    chat = "15/10/2026, 11:00 am - Sneha: Hello, this is Sneha from Navyug Broking Pvt Ltd. Scan and pay today only\n"
    c = _case(chat, images={"qr.png": _qr("upi://pay?pa=sunita.t@upi&pn=SUNITA%20TRADERS&am=25000")})
    add("payee hidden in a QR image", "QR names SUNITA TRADERS, no name check yet",
        "found + HUMAN_REVIEW", "found + " + (c.case_result() or "none") if c.payees else "not found")
    c = _case(chat, images={"qr.png": _qr("upi://pay?pa=navyug.brk@validhdfc&pn=NAVYUG%20BROKING%20PVT%20LTD")})
    add("payee hidden in a QR image", "QR copies the firm's name (pn is sender-typed); no name check",
        "not NO_MAJOR_ISSUE", "not NO_MAJOR_ISSUE" if c.case_result() != "NO_MAJOR_ISSUE" else "NO_MAJOR_ISSUE")

    # 4. Short / unclear voice note + pressure, no name check
    chat = ("16/10/2026, 9:20 pm - Max: Send ₹5,000 to trademaxpro@upi today only\n"
            "16/10/2026, 9:25 pm - Max: PTT-1.opus (file attached)\n")
    c = _case(chat)  # voice note referenced but not assessable
    d = c.decisions[0]
    add("short voice note + pressure", "0.3 s 'pay now' note, urgency in text",
        "INCONCLUSIVE + HIGH PRESSURE", f"{d.result}" + (" + HIGH PRESSURE" if d.reasons[0].startswith("HIGH PRESSURE") else ""))
    return rows


def summarize(rows: list[dict]) -> dict:
    expected_pass = [r for r in rows if not r["known_gap"]]
    gaps = [r for r in rows if r["known_gap"]]
    return {"cases": len(rows), "defended_attacks_passed": sum(r["pass"] for r in expected_pass),
            "defended_attacks": len(expected_pass), "known_gaps": len(gaps),
            "known_gaps_still_failing": sum(not r["pass"] for r in gaps), "rows": rows}


def write(summary: dict, out_dir: Path | None = None) -> Path:
    p = (out_dir or HERE) / "results_adversarial.json"
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(summary, indent=1, ensure_ascii=False))
    return p


def main(argv: list[str]) -> int:
    rows = run()
    summary = summarize(rows)
    write(summary)
    print(f"defended attacks passed: {summary['defended_attacks_passed']}/{summary['defended_attacks']}; "
          f"known gaps still failing: {summary['known_gaps_still_failing']}/{summary['known_gaps']}")
    print("| Group | Attack | Expected | Got | Result |\n|---|---|---|---|---|")
    for r in rows:
        res = "pass" if r["pass"] else ("KNOWN GAP" if r["known_gap"] else "FAIL")
        print(f"| {r['group']} | {r['attack']} | {r['expected']} | {r['got']} | {res} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
