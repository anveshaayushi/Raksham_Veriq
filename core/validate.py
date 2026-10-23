"""Validate golden fixtures against the shared contract.

Run:  python3 -m core.validate            (validates fixtures/scenario_*.json)
      python3 -m core.validate path.json  (validate specific files)
Exit code 0 = all good, 1 = problems (listed).

PLAIN WORDS: this checks that each fixture is internally honest. Every quoted
span really points at that text, every decision points at evidence that exists
and is allowed to decide, and the "worst payee wins" case result is right.

NOTE: this is a structural check, not the decision engine. Replaying the ladder
on the fixtures is done by tests in tests/rules once the engine exists.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from datetime import datetime
from typing import Any, Dict, List

from core.schemas import (
    CASE_LEVEL_PAYEE_ID, RESULT_RANK, AmountMention, CaseContext, CaseResult, Cue, Decision,
    Evidence, Indicator, Message, SchemaError, UserCheck, VoiceResult, NOT_A_GUARANTEE,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOP_KEYS = {"fixture_id", "schema_version", "synthetic", "description", "case", "input", "media",
            "user_checks", "reference", "registry_stub", "expected"}
EXPECTED_KEYS = {"messages", "indicators", "amounts", "cues", "voice_results", "evidence",
                 "decisions", "case_result", "variants"}
PAYEE_TYPES = ("upi_vpa", "bank_account")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def _android_prefix(m: Message) -> str:
    dt = datetime.fromisoformat(m.ts)
    h12 = dt.hour % 12 or 12
    ampm = "am" if dt.hour < 12 else "pm"
    return f"{dt.day:02d}/{dt.month:02d}/{dt.year}, {h12}:{dt.minute:02d} {ampm} - {m.sender}: "


def validate_fixture(data: Dict[str, Any]) -> List[str]:
    errs: List[str] = []

    def err(msg: str) -> None:
        errs.append(msg)

    if not isinstance(data, dict):
        return ["fixture is not a JSON object"]
    if set(data) != TOP_KEYS:
        err(f"top-level keys differ: missing={sorted(TOP_KEYS - set(data))} extra={sorted(set(data) - TOP_KEYS)}")
        return errs
    if data["synthetic"] is not True:
        err("fixture must be marked synthetic=true")
    exp = data["expected"]
    if set(exp) != EXPECTED_KEYS:
        err(f"expected keys differ: missing={sorted(EXPECTED_KEYS - set(exp))} extra={sorted(set(exp) - EXPECTED_KEYS)}")
        return errs

    # ---- parse every object through its contract -------------------------
    try:
        ctx = CaseContext.from_dict(data["case"])
        messages = [Message.from_dict(x) for x in exp["messages"]]
        indicators = [Indicator.from_dict(x) for x in exp["indicators"]]
        amounts = [AmountMention.from_dict(x) for x in exp["amounts"]]
        cues = [Cue.from_dict(x) for x in exp["cues"]]
        voices = [VoiceResult.from_dict(x) for x in exp["voice_results"]]
        evidence = [Evidence.from_dict(x) for x in exp["evidence"]]
        decisions = [Decision.from_dict(x) for x in exp["decisions"]]
        case_result = CaseResult.from_dict(exp["case_result"])
        user_checks = [UserCheck.from_dict(x) for x in data["user_checks"]]
    except SchemaError as e:
        return [f"schema: {e}"]

    # round trip: from_dict(to_dict(x)) must reproduce the JSON exactly
    for name, objs, raw in (("messages", messages, exp["messages"]), ("indicators", indicators, exp["indicators"]),
                            ("cues", cues, exp["cues"]), ("evidence", evidence, exp["evidence"]),
                            ("decisions", decisions, exp["decisions"])):
        if [o.to_dict() for o in objs] != raw:
            err(f"{name}: to_dict() does not round-trip to the JSON")

    # ---- messages and the raw chat text ----------------------------------
    by_id = {m.msg_id: m for m in messages}
    if len(by_id) != len(messages):
        err("duplicate msg_id")
    if [m.msg_id for m in messages] != sorted(by_id):
        err("messages must be in ascending msg_id order")
    chat = data["input"].get("chat_txt", "")
    transcripts = data["input"].get("transcripts", {})
    for m in messages:
        body = (m.media_ref + " (file attached)") if m.kind in ("voice", "image") else m.text
        if _android_prefix(m) + body not in chat:
            err(f"msg {m.msg_id}: line not found in chat_txt as '{_android_prefix(m)}{body[:30]}...'")
        if m.kind == "voice" and transcripts.get(m.media_ref, "") != m.text:
            err(f"msg {m.msg_id}: Message.text must equal transcripts[{m.media_ref!r}]")

    # ---- indicators -------------------------------------------------------
    ids = [i.id for i in indicators]
    if len(set(ids)) != len(ids):
        err("duplicate indicator id")
    for i in indicators:
        if i.case_id != ctx.case_id:
            err(f"{i.id}: case_id {i.case_id!r} != {ctx.case_id!r}")
        m = by_id.get(i.msg_id)
        if m is None:
            err(f"{i.id}: msg_id {i.msg_id} does not exist")
            continue
        if i.source in ("text", "voice"):
            if m.kind != i.source:
                err(f"{i.id}: source={i.source} but message {m.msg_id} kind={m.kind}")
            if m.text[i.span[0]:i.span[1]] != i.value_raw:
                err(f"{i.id}: text[{i.span}] = {m.text[i.span[0]:i.span[1]]!r} != value_raw {i.value_raw!r}")
        if i.source == "voice" and i.confidence == "high":
            err(f"{i.id}: voice-derived indicators must not be confidence=high (brief section 9)")
        if i.type == "upi_vpa" and (i.value_norm != i.value_norm.lower() or "@" not in i.value_norm):
            err(f"{i.id}: upi_vpa value_norm must be lower-case and contain '@'")
        if i.type == "bank_account" and not (i.value_norm.isdigit() and 9 <= len(i.value_norm) <= 18):
            err(f"{i.id}: bank_account value_norm must be 9-18 digits")
        if i.type == "ifsc" and not IFSC_RE.match(i.value_norm):
            err(f"{i.id}: ifsc value_norm does not match [A-Z]{{4}}0[A-Z0-9]{{6}}")
    payees = [i.id for i in indicators if i.type in PAYEE_TYPES]

    # ---- amounts, cues ----------------------------------------------------
    for a in amounts:
        m = by_id.get(a.msg_id)
        if m is None or m.text[a.span[0]:a.span[1]] != a.raw:
            err(f"amount in msg {a.msg_id}: span does not match raw {a.raw!r}")
        if a.payee_id not in payees:
            err(f"amount in msg {a.msg_id}: payee_id {a.payee_id!r} is not a payee indicator")
    for c in cues:
        m = by_id.get(c.msg_id)
        if m is None or c.excerpt not in m.text:
            err(f"cue {c.type} in msg {c.msg_id}: excerpt not found in message text")

    # ---- voice results ----------------------------------------------------
    voice_files = [m.media_ref for m in messages if m.kind == "voice"]
    if sorted(v.file_id for v in voices) != sorted(voice_files):
        err(f"voice_results file_ids {sorted(v.file_id for v in voices)} != voice messages {sorted(voice_files)}")

    # ---- evidence ---------------------------------------------------------
    ev_by_id = {e.evidence_id: e for e in evidence}
    if len(ev_by_id) != len(evidence):
        err("duplicate evidence_id")
    for e in evidence:
        if e.payee_id != CASE_LEVEL_PAYEE_ID and e.payee_id not in payees:
            err(f"{e.evidence_id}: payee_id {e.payee_id!r} is neither a payee indicator nor 'CASE'")
    a_names = {(e.payee_id, e.observed) for e in evidence if e.lane == "payee_name" and e.class_ == "A"}
    uc_names = {(u.payee_id, u.observed_name) for u in user_checks}
    if a_names != uc_names:
        err(f"class A payee_name evidence {sorted(a_names)} != user_checks {sorted(uc_names)}")
    for u in user_checks:
        if u.payee_id not in payees:
            err(f"user_check for unknown payee {u.payee_id!r}")

    # ---- decisions: one per payee, only allowed evidence decides ----------
    if [d.payee_id for d in decisions] != payees:
        err(f"decisions payees {[d.payee_id for d in decisions]} != payees in chat order {payees}")
    for d in decisions:
        cited = []
        for eid in d.evidence_ids:
            e = ev_by_id.get(eid)
            if e is None:
                err(f"{d.payee_id}: cites unknown evidence {eid}")
                continue
            if e.payee_id not in (d.payee_id, CASE_LEVEL_PAYEE_ID):
                err(f"{d.payee_id}: cites {eid} which belongs to payee {e.payee_id}")
            cited.append(e)
        classes = {(e.lane, e.class_) for e in cited}
        if d.result == "NAME_DISCREPANCY" and ("payee_name", "A") not in classes:
            err(f"{d.payee_id}: NAME_DISCREPANCY needs class A payee_name evidence (class D never decides)")
        if d.result == "NO_MAJOR_ISSUE" and ("payee_name", "A") not in classes:
            err(f"{d.payee_id}: NO_MAJOR_ISSUE needs class A payee_name evidence")
        if d.result == "NO_MAJOR_ISSUE" and any(e.class_ == "E" for e in cited):
            err(f"{d.payee_id}: model output (class E) must not be cited to clear a payee (invariant 2)")
        if d.result == "REGISTRATION_CONFLICT" and not any(l == "registration" for l, _ in classes):
            err(f"{d.payee_id}: REGISTRATION_CONFLICT needs registration evidence")
        if d.result == "LINKED" and ("registry", "C") not in classes:
            err(f"{d.payee_id}: LINKED needs class C registry evidence")
        if d.result in ("NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "LINKED", "NO_MAJOR_ISSUE") \
                and all(e.class_ == "D" for e in cited):
            err(f"{d.payee_id}: decided on class D only")

    # ---- registry stub agrees with LINKED --------------------------------
    stub = data["registry_stub"]
    if sorted(stub) != sorted(payees):
        err(f"registry_stub keys {sorted(stub)} != payees {sorted(payees)}")
    for pid, status in stub.items():
        if status not in ("clean", "linked"):
            err(f"registry_stub[{pid}]={status!r} must be 'clean' or 'linked'")
        if status == "linked" and not any(d.payee_id == pid and d.result == "LINKED" for d in decisions):
            err(f"registry_stub says {pid} is linked but its decision is not LINKED")

    # ---- case result = worst payee, ties go to first in chat order --------
    if decisions:
        worst = min(decisions, key=lambda d: (RESULT_RANK[d.result], payees.index(d.payee_id)))
        if (case_result.result, case_result.deciding_payee_id) != (worst.result, worst.payee_id):
            err(f"case_result {case_result.result}/{case_result.deciding_payee_id} != worst payee "
                f"{worst.result}/{worst.payee_id}")
        if case_result.next_step != worst.next_step:
            err("case_result.next_step must equal the deciding payee's next_step")
    if case_result.case_id != ctx.case_id or case_result.money_already_sent != ctx.money_already_sent:
        err("case_result case_id / money_already_sent do not match the case context")
    if case_result.result == "NO_MAJOR_ISSUE" and NOT_A_GUARANTEE not in case_result.next_step:
        err("NO_MAJOR_ISSUE case result lacks the guarantee disclaimer")

    # ---- variants ---------------------------------------------------------
    v = exp["variants"].get("money_already_sent_true", {})
    if not (v.get("result_unchanged") is True and "1930" in v.get("next_step_must_contain", [])):
        err("variants.money_already_sent_true must say result_unchanged=true and require '1930' in next_step")
    return errs


def validate_reference(path: pathlib.Path) -> List[str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        datetime.fromisoformat(d["as_of"])
        assert isinstance(d["entries"], list) and all({"reg_no", "entity"} <= set(e) for e in d["entries"])
        assert "SYNTHETIC" in d["source"]
    except Exception as e:  # noqa: BLE001 - report any problem as a validation error
        return [f"{path.name}: {e!r}"]
    return []


def main(argv: List[str]) -> int:
    paths = [pathlib.Path(a) for a in argv] or sorted((ROOT / "fixtures").glob("scenario_*.json"))
    if not paths:
        print("no fixtures found")
        return 1
    bad = 0
    for p in paths:
        problems = validate_fixture(json.loads(p.read_text(encoding="utf-8")))
        print(("OK   " if not problems else "FAIL ") + p.name)
        for pr in problems:
            print("   -", pr)
        bad += bool(problems)
    if not argv:
        for p in sorted((ROOT / "fixtures" / "reference").glob("*.json")):
            problems = validate_reference(p)
            print(("OK   " if not problems else "FAIL ") + "reference/" + p.name)
            for pr in problems:
                print("   -", pr)
            bad += bool(problems)
    print(f"{'ALL VALID' if not bad else str(bad) + ' file(s) FAILED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
