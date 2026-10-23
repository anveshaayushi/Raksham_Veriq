#!/usr/bin/env python3
"""Generates fixtures/scenario_*.json and fixtures/reference/sebi_snapshot_synthetic.json.

Run:  python3 fixtures/build_fixtures.py

The generated JSON files are the golden source. This script only exists so that
every span offset is computed from the message text instead of hand-counted.
Everything here is SYNTHETIC. Names, UPI IDs, accounts and SEBI numbers are
fictional (SEBI numbers carry a DEMO marker so they cannot collide with real
registrations). Voice results are STUB values, not measurements.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
AS_OF = "2026-10-23"
TZ = "+05:30"
UPI_SRC = "user-reported: UPI/bank app payee-name display (typed by the user)"
SNAP_SRC = "dated public-list snapshot (SYNTHETIC fixture: fixtures/reference/sebi_snapshot_synthetic.json)"
VOICE_SRC = "voice detector STUB (fixture value, not a measurement)"
REG_SRC = "cross-victim registry STUB (fixture lookup table)"


def iso(d, h, mi):
    return f"2026-10-{d:02d}T{h:02d}:{mi:02d}:00{TZ}"


def android_prefix(ts, sender):
    """WhatsApp Android line start, e.g. '13/10/2026, 6:02 pm - Name: '."""
    day, month, year = int(ts[8:10]), int(ts[5:7]), int(ts[0:4])
    hour, minute = int(ts[11:13]), int(ts[14:16])
    h12 = hour % 12 or 12
    ampm = "am" if hour < 12 else "pm"
    return f"{day:02d}/{month:02d}/{year}, {h12}:{minute:02d} {ampm} - {sender}: "


SYSTEM_LINE = ("13/10/2026, 5:58 pm - Messages and calls are end-to-end encrypted. "
               "No one outside of this chat, not even WhatsApp, can read or listen to them.")


def span(text, sub):
    i = text.find(sub)
    assert i >= 0, f"{sub!r} not in {text!r}"
    assert text.find(sub, i + 1) == -1, f"{sub!r} occurs twice in {text!r}"
    return [i, i + len(sub)]


def build(case_id, firm, description, msgs, indicators, amounts, cues, voice, evidence,
          decisions, user_checks, registry_stub, case_result, variants):
    messages = [
        {"msg_id": i, "ts": ts, "sender": s, "kind": k, "text": t, "media_ref": m}
        for i, (ts, s, k, t, m) in enumerate(msgs, start=1)
    ]
    by_id = {m["msg_id"]: m for m in messages}

    lines = [SYSTEM_LINE]
    transcripts = {}
    media = []
    for m in messages:
        pre = android_prefix(m["ts"], m["sender"])
        if m["kind"] == "voice":
            lines.append(pre + m["media_ref"] + " (file attached)")
            transcripts[m["media_ref"]] = m["text"]
            media.append({"media_ref": m["media_ref"], "kind": "audio", "file_present": False,
                          "note": "synthetic audio not yet supplied; use the stub VoiceResult"})
        else:
            lines.append(pre + m["text"])

    ind = []
    for n, (typ, raw, norm, mid, src, conf) in enumerate(indicators, start=1):
        ind.append({"id": f"{case_id}-I{n}", "case_id": case_id, "msg_id": mid, "type": typ,
                    "value_norm": norm, "value_raw": raw, "source": src, "confidence": conf,
                    "span": span(by_id[mid]["text"], raw)})
    pid = lambda n: f"{case_id}-I{n}"  # noqa: E731

    amt = [{"msg_id": mid, "payee_id": pid(pn), "value_inr": val, "raw": raw,
            "span": span(by_id[mid]["text"], raw)} for (mid, raw, val, pn) in amounts]
    cue = [{"msg_id": mid, "type": t, "severity": sev, "excerpt": ex} for (mid, t, sev, ex) in cues]
    for c in cue:
        assert c["excerpt"] in by_id[c["msg_id"]]["text"], c

    data = {
        "fixture_id": case_id,
        "schema_version": "0.1.0-c0",
        "synthetic": True,
        "description": description,
        "case": {"case_id": case_id, "claimed_firm": firm, "money_already_sent": False, "as_of": AS_OF},
        "input": {
            "platform": "whatsapp_android",
            "chat_txt": "\n".join(lines) + "\n",
            "parser_skips_system_lines": True,
            "transcripts": transcripts,
        },
        "media": media,
        "user_checks": [{"payee_id": pid(pn), "observed_name": name, "source": UPI_SRC, "as_of": AS_OF}
                        for (pn, name) in user_checks],
        "reference": {"sebi_snapshot": "fixtures/reference/sebi_snapshot_synthetic.json"},
        "registry_stub": {pid(pn): status for pn, status in registry_stub},
        "expected": {
            "messages": messages,
            "indicators": ind,
            "amounts": amt,
            "cues": cue,
            "voice_results": voice,
            "evidence": [{"evidence_id": f"{case_id}-E{n}", **(
                {**e, "payee_id": e["payee_id"] if e["payee_id"] == "CASE" else pid(int(e["payee_id"]))})}
                for n, e in enumerate(evidence, start=1)],
            "decisions": [{"payee_id": pid(pn), "result": r, "rule_id": rule, "reasons": reasons,
                           "evidence_ids": [f"{case_id}-E{x}" for x in ev], "next_step": step}
                          for (pn, r, rule, reasons, ev, step) in decisions],
            "case_result": None,  # filled below
            "variants": variants,
        },
    }
    cr = dict(case_result)
    n = cr.pop("deciding_payee_n")
    data["expected"]["case_result"] = {"case_id": case_id, **cr, "deciding_payee_id": pid(n),
                                       "money_already_sent": False}
    return data


def ev(payee, lane, cls, claimed, observed, source, limitation, as_of=AS_OF):
    return {"payee_id": str(payee) if payee != "CASE" else "CASE", "lane": lane, "class": cls,
            "claimed": claimed, "observed": observed, "source": source, "as_of": as_of,
            "limitation": limitation}


LIM_NAME_DIFF = ("Shows the displayed name differs from the claim. Does not prove fraud or who controls the account.")
LIM_NAME_MATCH = ("A matching name does not prove the firm is legitimate (shell or mule accounts can copy a name).")
LIM_REG_REG = "Absence from a local, dated snapshot can mean the snapshot is incomplete or out of date. Not verification of any payee."
LIM_REG_OK = "A listing does not show who owns a UPI ID or account. Not verification of the payee."
LIM_VOICE = "A no_signal result does not mean the voice is genuine and never clears a payee."
LIM_REG_CLEAN = "Absence from the registry means nobody has reported it here, not that it is safe."

STEP_PAUSE = ("Pause: don't pay until you verify. Contact the organisation through a number or website you "
              "find yourself, not one from this chat. If money was sent, call 1930.")
STEP_C = ("Don't pay yet. Find the firm's contact yourself, not from the chat. If money was sent, call 1930.")
STEP_B = ("Checks run found no major issue. This is not a guarantee. Before paying, confirm the firm's contact "
          "details through a number or website you find yourself.")


def v_result(file_id, state, score, thr, secs, reasons):
    return {"file_id": file_id, "state": state, "score": score, "threshold": thr,
            "speech_seconds": secs, "reasons": reasons, "model_version": "stub-fixture-v0"}


# --------------------------------------------------------------------------- A
def scenario_a():
    cid = "A_meera"
    firm = "Navyug Wealth Research Pvt Ltd"
    voice_file = "PTT-20261017-WA0004.opus"
    msgs = [
        (iso(13, 18, 2), "Rahul Navyug", "text",
         "Namaste Meera ji. I am Rahul, head of research at Navyug Wealth. We are SEBI registered, reg no INH000DEMO45.", None),
        (iso(13, 18, 5), "Meera", "text", "Okay, what do I need to do?", None),
        (iso(14, 10, 11), "Rahul Navyug", "text", "Onboarding fee ₹10,000. UPI: ramesh.k@upi", None),
        (iso(17, 9, 40), "Rahul Navyug", "voice",
         "Ma'am, the payment department has a new ID, sunita.t@upi. Please send ₹25,000 today only.", voice_file),
        (iso(19, 16, 20), "Rahul Navyug", "text",
         "Profit is ready. Pay 18% tax to withdraw.\n₹60,000 to A/c 30112233445021 IFSC SBIN0001234, today only.", None),
        (iso(19, 16, 31), "Meera", "text", "Ok, sending now", None),
    ]
    indicators = [
        ("firm_name", "Navyug Wealth", "navyug wealth", 1, "text", "high"),          # I1
        ("sebi_reg", "INH000DEMO45", "INH000DEMO45", 1, "text", "high"),             # I2
        ("upi_vpa", "ramesh.k@upi", "ramesh.k@upi", 3, "text", "high"),              # I3 payee 1
        ("upi_vpa", "sunita.t@upi", "sunita.t@upi", 4, "voice", "medium"),           # I4 payee 2 (from transcript)
        ("bank_account", "30112233445021", "30112233445021", 5, "text", "high"),     # I5 payee 3
        ("ifsc", "SBIN0001234", "SBIN0001234", 5, "text", "high"),                   # I6
    ]
    amounts = [(3, "₹10,000", 10000, 3), (4, "₹25,000", 25000, 4), (5, "₹60,000", 60000, 5)]
    cues = [
        (1, "authority_claim", "soft", "We are SEBI registered"),
        (4, "payee_change", "soft", "has a new ID, sunita.t@upi"),
        (4, "urgency", "soft", "today only"),
        (5, "fee_to_withdraw", "hard", "Pay 18% tax to withdraw"),
        (5, "payee_change", "soft", "₹60,000 to A/c 30112233445021"),
        (5, "urgency", "soft", "today only"),
    ]
    voice = [v_result(voice_file, "no_signal", 0.12, 0.5, 5.0, [])]
    claim = f"payee belongs to {firm}"
    evidence = [
        ev("3", "payee_name", "A", claim, "SHREE GANESH TRADERS", UPI_SRC, LIM_NAME_DIFF),            # E1
        ev("4", "payee_name", "A", claim, "OM SAI ENTERPRISES", UPI_SRC, LIM_NAME_DIFF),             # E2
        ev("5", "payee_name", "A", claim, "KALPANA TRADING CO", UPI_SRC, LIM_NAME_DIFF),             # E3
        ev("CASE", "registration", "B", f"SEBI reg INH000DEMO45 quoted for {firm} (msg 1)",
           "INH000DEMO45 not present in the snapshot", SNAP_SRC, LIM_REG_REG),                       # E4
        ev("4", "voice", "E", f"voice note msg 4 ({voice_file})",
           "no_signal (stub score 0.12 vs stub threshold 0.50)", VOICE_SRC, LIM_VOICE),              # E5
        ev("3", "registry", "C", "payee ramesh.k@upi", "no matching report (stub)", REG_SRC, LIM_REG_CLEAN),   # E6
        ev("4", "registry", "C", "payee sunita.t@upi", "no matching report (stub)", REG_SRC, LIM_REG_CLEAN),   # E7
        ev("5", "registry", "C", "payee A/c 30112233445021", "no matching report (stub)", REG_SRC, LIM_REG_CLEAN),  # E8
    ]
    def disc(name, extra):
        return [f"Class A (user-reported): app shows '{name}'; no shared distinctive word with claimed '{firm}'."] + extra
    outranked = "Also present but outranked: SEBI number INH000DEMO45 not in the dated snapshot (REG_CONFLICT)."
    decisions = [
        (3, "NAME_DISCREPANCY", "NAME_DISC", disc("SHREE GANESH TRADERS", [outranked]), [1], STEP_PAUSE),
        (4, "NAME_DISCREPANCY", "NAME_DISC",
         disc("OM SAI ENTERPRISES", [outranked, "Voice note: no_signal. Does not clear or accuse."]), [2], STEP_PAUSE),
        (5, "NAME_DISCREPANCY", "NAME_DISC", disc("KALPANA TRADING CO", [outranked]), [3], STEP_PAUSE),
    ]
    case_result = {"result": "NAME_DISCREPANCY", "rule_id": "NAME_DISC", "deciding_payee_n": 3, "next_step": STEP_PAUSE}
    variants = {"money_already_sent_true": {
        "result_unchanged": True, "next_step_must_contain": ["1930"],
        "note": "Invariant 6: the toggle changes next_step only, never the result."}}
    return build(cid, firm,
                 "Suspicious: one claimed firm, three different payees, payee rotation, fee to withdraw. "
                 "Multiline message in msg 5; voice-derived payee in msg 4; unrecognised SEBI number.",
                 msgs, indicators, amounts, cues, voice, evidence, decisions,
                 [(3, "SHREE GANESH TRADERS"), (4, "OM SAI ENTERPRISES"), (5, "KALPANA TRADING CO")],
                 [(3, "clean"), (4, "clean"), (5, "clean")], case_result, variants)


# --------------------------------------------------------------------------- B
def scenario_b():
    cid = "B_ankit"
    firm = "Navyug Broking Pvt Ltd"
    voice_file = "PTT-20261016-WA0005.opus"
    msgs = [
        (iso(15, 11, 0), "Sneha Navyug", "text",
         "Hello Ankit, this is Sneha from Navyug Broking Pvt Ltd. Your account opening is complete. SEBI reg no INZ000DEMO01.", None),
        (iso(15, 11, 3), "Ankit", "text", "Thanks. How do I add funds?", None),
        (iso(15, 11, 6), "Sneha Navyug", "text",
         "You can add funds to our collection account on UPI: navyug.brk@validhdfc. Please confirm the payee name on your app before paying.", None),
        (iso(15, 11, 20), "Ankit", "text", "Okay, I will check my app first.", None),
        (iso(16, 10, 30), "Sneha Navyug", "voice",
         "Hi Ankit, your funds have been received. Thank you for choosing us.", voice_file),
    ]
    indicators = [
        ("firm_name", "Navyug Broking Pvt Ltd", "navyug broking pvt ltd", 1, "text", "high"),   # I1
        ("sebi_reg", "INZ000DEMO01", "INZ000DEMO01", 1, "text", "high"),                       # I2
        ("upi_vpa", "navyug.brk@validhdfc", "navyug.brk@validhdfc", 3, "text", "high"),        # I3 payee
    ]
    voice = [v_result(voice_file, "no_signal", 0.08, 0.5, 4.0, [])]
    evidence = [
        ev("3", "payee_name", "A", f"payee belongs to {firm}", "NAVYUG BROKING PRIVATE LIMITED", UPI_SRC, LIM_NAME_MATCH),  # E1
        ev("CASE", "registration", "B", f"SEBI reg INZ000DEMO01 quoted for {firm} (msg 1)",
           "Listed as 'Navyug Broking Private Limited' in the snapshot", SNAP_SRC, LIM_REG_OK),                              # E2
        ev("3", "registry", "C", "payee navyug.brk@validhdfc", "no matching report (stub)", REG_SRC, LIM_REG_CLEAN),          # E3
        ev("CASE", "voice", "E", f"voice note msg 5 ({voice_file})",
           "no_signal (stub score 0.08 vs stub threshold 0.50)", VOICE_SRC, LIM_VOICE),                                      # E4
    ]
    reasons = [
        "Class A (user-reported): app shows 'NAVYUG BROKING PRIVATE LIMITED', which shares distinctive words with the claimed firm.",
        "SEBI number INZ000DEMO01 is in the dated snapshot under a matching entity (class B; not verification of the payee).",
        "Registry: no reports (stub). No hard pressure cues. No voice flag.",
    ]
    decisions = [(3, "NO_MAJOR_ISSUE", "CLEAR", reasons, [1, 2, 3], STEP_B)]
    case_result = {"result": "NO_MAJOR_ISSUE", "rule_id": "CLEAR", "deciding_payee_n": 3, "next_step": STEP_B}
    variants = {"money_already_sent_true": {
        "result_unchanged": True, "next_step_must_contain": ["1930", "This is not a guarantee."],
        "note": "Invariant 6; the disclaimer must survive the toggle."}}
    return build(cid, firm, "Legitimate broker: payee name matches, registration consistent, no pressure cues.",
                 msgs, indicators, [], [], voice, evidence, decisions,
                 [(3, "NAVYUG BROKING PRIVATE LIMITED")], [(3, "clean")], case_result, variants)


# --------------------------------------------------------------------------- C
def scenario_c():
    cid = "C_priya"
    firm = "TradeMax Pro"
    voice_file = "PTT-20261016-WA0004.opus"
    msgs = [
        (iso(16, 21, 15), "Max Admin", "text",
         "Priya, join TradeMax Pro today. Guaranteed 3x returns in 30 days, today only!", None),
        (iso(16, 21, 17), "Priya", "text", "Where do I pay?", None),
        (iso(16, 21, 20), "Max Admin", "text", "Send ₹5,000 to trademaxpro@upi to start.", None),
        (iso(16, 21, 25), "Max Admin", "voice", "", voice_file),
    ]
    indicators = [
        ("firm_name", "TradeMax Pro", "trademax pro", 1, "text", "high"),            # I1
        ("upi_vpa", "trademaxpro@upi", "trademaxpro@upi", 3, "text", "high"),        # I2 payee
    ]
    amounts = [(3, "₹5,000", 5000, 2)]
    cues = [
        (1, "guaranteed_return", "hard", "Guaranteed 3x returns"),
        (1, "urgency", "soft", "today only"),
    ]
    voice = [v_result(voice_file, "cant_assess", None, None, 0.4, ["too_little_speech"])]
    evidence = [
        ev("CASE", "voice", "E", f"voice note msg 4 ({voice_file})",
           "cant_assess: too little speech (0.4 s, stub)", VOICE_SRC,
           "Can't assess means no opinion either way. It is not a clearance."),                                  # E1
        ev("2", "registry", "C", "payee trademaxpro@upi", "no matching report (stub)", REG_SRC, LIM_REG_CLEAN),  # E2
    ]
    reasons = [
        "No class A evidence for trademaxpro@upi: the user has not run a bank/UPI-app name check.",
        "Voice note: can't assess (too little speech).",
        "Hard cue: guaranteed_return in msg 1.",
    ]
    decisions = [(2, "INCONCLUSIVE", "INCONCL", reasons, [1], STEP_C)]
    case_result = {"result": "INCONCLUSIVE", "rule_id": "INCONCL", "deciding_payee_n": 2, "next_step": STEP_C}
    variants = {"money_already_sent_true": {
        "result_unchanged": True, "next_step_must_contain": ["1930"],
        "note": "Invariant 6."}}
    return build(cid, firm, "Inconclusive: no official name check, guaranteed-return claim, voice note too short to assess.",
                 msgs, indicators, amounts, cues, voice, evidence, decisions,
                 [], [(2, "clean")], case_result, variants)


def main():
    (ROOT / "reference").mkdir(exist_ok=True)
    snapshot = {
        "as_of": AS_OF,
        "source": "SYNTHETIC fixture. Not the real SEBI list. Registration numbers carry a DEMO marker.",
        "entries": [
            {"reg_no": "INZ000DEMO01", "entity": "Navyug Broking Private Limited", "category": "Stock Broker"},
        ],
    }
    (ROOT / "reference" / "sebi_snapshot_synthetic.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, fn in (("scenario_A_suspicious", scenario_a), ("scenario_B_legitimate", scenario_b),
                     ("scenario_C_inconclusive", scenario_c)):
        (ROOT / f"{name}.json").write_text(json.dumps(fn(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", f"fixtures/{name}.json")


if __name__ == "__main__":
    main()
