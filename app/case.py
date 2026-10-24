"""Assemble a case from inputs, with no Streamlit dependency (so it is testable).

Two paths, and the UI always says which one produced the answer:

* Demo scenarios use Claude A's golden fixtures (fixtures/scenario_*.json). While the user's inputs equal the
  fixture's inputs (same chat, firm, typed names, and the same voice state), the app shows the fixture's EXPECTED
  messages, indicators, evidence and decisions. These are Claude A's hand-specified expected values, not engine output.
* Anything else goes through the adapters: Claude A's parser/extractor/rules when they exist, otherwise labelled stubs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from registry.interface import RegistryResult
from registry.sqlite_registry import from_env as sqlite_registry_from_env
from registry.stub import StubRegistry
from report.build import PayeeRow, ReportData

from .adapters import decide as decide_adapter
from .adapters import extract as extract_adapter
from .adapters import voice as voice_adapter
from .contracts import Cue, Decision, Evidence, Indicator, Message, VoiceResult, case_result, evidence_class, from_json, get
from .evidence_input import SOURCES, payee_name_evidence
from .intake import safe_name
from .next_steps import display_next_step, with_money_sent

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = {"A": "scenario_A_suspicious.json", "B": "scenario_B_legitimate.json", "C": "scenario_C_inconclusive.json"}
CASE_LEVEL = "CASE"


def load_demo(sid: str) -> dict:
    """Claude A's golden fixture for scenario A, B or C."""
    if sid not in FIXTURES:
        raise ValueError("unknown demo scenario")
    return json.loads((ROOT / "fixtures" / FIXTURES[sid]).read_text(encoding="utf-8"))


def demo_title(fx: dict) -> str:
    return f"Scenario {fx['fixture_id'][0]} ({fx['fixture_id']}): {fx['description']}"


def demo_inputs(fx: dict) -> dict:
    """What the UI pre-fills for a demo: chat, transcripts, firm, and the typed names keyed by payee value."""
    by_id = {i["id"]: i for i in fx["expected"]["indicators"]}
    checks = {by_id[u["payee_id"]]["value_norm"]: {"name": u["observed_name"], "source": SOURCES[1],
                                                   "date": date.fromisoformat(u["as_of"])} for u in fx["user_checks"]}
    return {"chat_text": fx["input"]["chat_txt"], "transcripts": fx["input"].get("transcripts", {}),
            "claimed_firm": fx["case"]["claimed_firm"], "case_id": fx["case"]["case_id"], "checks": checks,
            "as_of": date.fromisoformat(fx["case"]["as_of"])}


@dataclass
class UserCheck:
    observed_name: str
    source: str
    as_of: date


@dataclass
class Case:
    case_id: str
    claimed_firm: str
    extraction: extract_adapter.Extraction
    payees: list
    evidence: list
    voice: list
    voice_is_stub: bool
    registry: list
    bundle: decide_adapter.DecisionBundle
    files: list[dict]
    amounts: dict[str, str] = field(default_factory=dict)  # payee_id -> raw amount text
    fixture_id: str | None = None

    @property
    def decisions(self) -> list:
        return self.bundle.decisions

    def result_for(self, payee_id: str):
        return next((d for d in self.decisions if get(d, "payee_id") == payee_id), None)

    def case_result(self) -> str | None:
        return case_result(self.decisions)

    def evidence_for(self, payee_id: str) -> list:
        """Evidence cited by the payee's decision, plus the payee's own evidence (deduplicated, in order)."""
        d = self.result_for(payee_id)
        ids = list(get(d, "evidence_ids") or []) if d is not None else []
        ids += [get(e, "evidence_id") for e in self.evidence if get(e, "payee_id") == payee_id]
        by_id = {get(e, "evidence_id"): e for e in self.evidence}
        return [by_id[i] for i in dict.fromkeys(ids) if i in by_id]

    def case_level_evidence(self) -> list:
        return [e for e in self.evidence if get(e, "payee_id") == CASE_LEVEL]


# ------------------------------------------------------------------ extraction ----
def golden_extraction(fx: dict) -> extract_adapter.Extraction:
    e = fx["expected"]
    return extract_adapter.Extraction(
        messages=[from_json(Message, m) for m in e["messages"]],
        indicators=[from_json(Indicator, i) for i in e["indicators"]],
        cues=[from_json(Cue, c) for c in e["cues"]],
        source=f"Claude A's golden fixture {fx['fixture_id']} (expected values; parser/extractor not built yet)",
        is_stub=True)


def engine_available() -> bool:
    """True when the real parser, extractor and rules (FINALE) are importable with the contract's entry points."""
    try:
        import extract as _e  # type: ignore
        import parsing as _p  # type: ignore
        import rules as _r  # type: ignore
    except ImportError:
        return False
    return all(hasattr(m, f) for m, f in ((_p, "parse_chat"), (_e, "extract"), (_r, "decide"), (_r, "case_evidence")))


def extract(case_id: str, chat_text: str, transcripts: dict | None = None, fixture: dict | None = None) -> extract_adapter.Extraction:
    if fixture is not None and chat_text == fixture["input"]["chat_txt"] and not engine_available():
        return golden_extraction(fixture)
    return extract_adapter.run(chat_text, case_id, transcripts)


# ------------------------------------------------------------------ voice ----
def _voice_results(ex, audio: dict[str, bytes], fixture: dict | None) -> tuple[list, bool]:
    voice, stub = [], False
    audio = {safe_name(k): v for k, v in (audio or {}).items()}
    fx_voice = {v["file_id"]: v for v in (fixture or {}).get("expected", {}).get("voice_results", [])}
    for m in ex.messages:
        if get(m, "kind") != "voice":
            continue
        ref = get(m, "media_ref") or f"msg{get(m, 'msg_id')}"
        if fixture is not None and ref in fx_voice:
            b = None
            try:
                b = voice_adapter.demo_stub(fixture["fixture_id"][0], ref)  # Claude B's voice/stub.py, if present
            except Exception:
                b = None
            voice.append(b if b is not None else from_json(VoiceResult, fx_voice[ref]))
            stub = True
        elif safe_name(ref) in audio:
            vr, is_stub = voice_adapter.analyse(ref, audio[safe_name(ref)], ref)
            voice.append(vr)
            stub = stub or is_stub
        else:
            voice.append(VoiceResult(file_id=ref, state="cant_assess", score=None, threshold=None, speech_seconds=0.0,
                                     reasons=["The voice note is mentioned in the chat but the file was not uploaded."],
                                     model_version="none"))
    return voice, stub


# ------------------------------------------------------------------ build ----
def _fixture_inputs_match(fx: dict, chat_text: str, claimed_firm: str, checks: dict[str, UserCheck], voice: list) -> bool:
    want = demo_inputs(fx)
    given = {k: c.observed_name.strip() for k, c in checks.items() if c.observed_name.strip()}
    want_names = {k: v["name"] for k, v in want["checks"].items()}
    want_voice = [v["state"] for v in fx["expected"]["voice_results"]]
    return (chat_text == want["chat_text"] and claimed_firm.strip() == want["claimed_firm"] and given == want_names
            and [get(v, "state") for v in voice] == want_voice)


def build_case(*, case_id: str, chat_text: str, claimed_firm: str, checks: dict[str, UserCheck],
               audio: dict[str, bytes] | None = None, files: list[dict] | None = None, transcripts: dict | None = None,
               fixture: dict | None = None) -> Case:
    ex = extract(case_id, chat_text, transcripts, fixture)
    payees = extract_adapter.payees(ex.indicators)
    voice, voice_stub = _voice_results(ex, audio or {}, fixture)

    if engine_available():
        return _computed_case(case_id=case_id, chat_text=chat_text, claimed_firm=claimed_firm, checks=checks, ex=ex,
                              payees=payees, voice=voice, voice_stub=voice_stub, files=files, fixture=fixture)

    if fixture is not None and _fixture_inputs_match(fixture, chat_text, claimed_firm, checks, voice):
        e = fixture["expected"]
        evidence = [from_json(Evidence, x) for x in e["evidence"]]
        decisions = [from_json(Decision, x) for x in e["decisions"]]
        registry = [RegistryResult(p.id, fixture["registry_stub"].get(p.id, "unavailable"), 0, False,
                                   "registry STUB values from Claude A's golden fixture") for p in payees]
        amounts = {a["payee_id"]: a["raw"] for a in e["amounts"]}
        bundle = decide_adapter.DecisionBundle(
            decisions, f"Claude A's golden fixture {fixture['fixture_id']} (expected values; rules engine not built yet)", True,
            ["These are the results Claude A's golden fixture expects. No rules engine ran."])
        return Case(fixture["case"]["case_id"], claimed_firm, ex, payees, evidence, voice, voice_stub, registry, bundle,
                    files or [], amounts, fixture["fixture_id"])

    evidence = []
    for p in payees:
        c = checks.get(p.value_norm)
        if c is not None:
            ev = payee_name_evidence(f"{case_id}-E{len(evidence) + 1}", p.id, claimed_firm, c.observed_name, c.source, c.as_of)
            if ev is not None:
                evidence.append(ev)
    reg = sqlite_registry_from_env() or StubRegistry()  # SQLite only when VERIQ_REGISTRY_DB is set
    registry = [reg.lookup(p.id, p.type, p.value_norm) for p in payees]
    bundle = decide_adapter.decide(claimed_firm=claimed_firm, payees=payees, indicators=ex.indicators, cues=ex.cues,
                                   evidence=evidence, voice=voice, registry=registry)
    if fixture is not None:
        bundle.notes.append("You changed the demo's inputs, so Claude A's expected results no longer apply.")
    msgs = {get(m, "msg_id"): m for m in ex.messages}
    amounts = {}
    for p in payees:
        amt = extract_adapter.amount_in(get(msgs.get(p.msg_id), "text", "") if p.msg_id in msgs else "")
        if amt:
            amounts[p.id] = amt
    return Case(case_id, claimed_firm, ex, payees, evidence, voice, voice_stub, registry, bundle, files or [], amounts,
                fixture["fixture_id"] if fixture else None)


def _computed_case(*, case_id, chat_text, claimed_firm, checks, ex, payees, voice, voice_stub, files, fixture) -> Case:
    """FINALE path: every answer is computed by rules.decide from the parsed chat, the user's name checks, the
    registration snapshot, the voice results and the registry. Demos run through the same code."""
    import extract as a_extract  # type: ignore
    import rules  # type: ignore

    if fixture is not None:
        case_id = fixture["case"]["case_id"]
        ex = extract_adapter.run(chat_text, case_id, fixture["input"].get("transcripts"))
        payees = extract_adapter.payees(ex.indicators)
    as_of = date.today().isoformat()
    name_ev = []
    for p in payees:
        c = checks.get(p.value_norm)
        if c is not None:
            e = payee_name_evidence(f"{case_id}-E{len(name_ev) + 1}", p.id, claimed_firm, c.observed_name, c.source,
                                    c.as_of)
            if e is not None:
                name_ev.append(e)
    reg = sqlite_registry_from_env()
    if reg is not None:
        registry = [reg.lookup(p.id, p.type, p.value_norm) for p in payees]
    elif fixture is not None:
        registry = [RegistryResult(p.id, fixture["registry_stub"].get(p.id, "unavailable"), 0, False,
                                   "registry STUB (demo fixture table)") for p in payees]
    else:
        registry = [StubRegistry().lookup(p.id, p.type, p.value_norm) for p in payees]
    evidence = rules.case_evidence(case_id=case_id, claimed_firm=claimed_firm, messages=ex.messages,
                                   indicators=ex.indicators, payees=payees, payee_name_evidence=name_ev, voice=voice,
                                   registry=registry, as_of=as_of)
    bundle = decide_adapter.decide(claimed_firm=claimed_firm, payees=payees, indicators=ex.indicators, cues=ex.cues,
                                   evidence=evidence, voice=voice, registry=registry)
    if voice_stub:
        bundle.notes.append("Voice results are stub values (no calibrated detector connected); they can only raise caution.")
    amounts = {}
    if hasattr(a_extract, "amounts"):
        amounts = {a.payee_id: a.raw for a in a_extract.amounts(ex.messages, ex.indicators)}
    return Case(case_id, claimed_firm, ex, payees, evidence, voice, voice_stub, registry, bundle, files or [], amounts,
                fixture["fixture_id"] if fixture else None)


# ------------------------------------------------------------------ reports ----
def report_data(case: Case, *, money_sent: bool, user: dict[str, str] | None = None,
                per_payee: dict[str, dict[str, str]] | None = None) -> ReportData:
    user = user or {}
    per_payee = per_payee or {}
    msgs = {get(m, "msg_id"): m for m in case.extraction.messages}
    voice_by_ref = {get(v, "file_id"): v for v in case.voice}
    rows = []
    for p in case.payees:
        d = with_money_sent(case.result_for(p.id), money_sent)
        msg_ids = sorted({get(i, "msg_id") for i in case.extraction.indicators if get(i, "value_norm") == p.value_norm})
        first = msgs.get(msg_ids[0]) if msg_ids else None
        vnote = None
        if first is not None and get(first, "kind") == "voice":
            v = voice_by_ref.get(get(first, "media_ref"))
            if v is not None:
                vnote = (f"payee taken from a voice-note transcript; voice check: {get(v, 'state')} "
                         f"({'; '.join(get(v, 'reasons') or []) or 'no reasons given'}; {voice_adapter.score_display(v)})")
        pp = per_payee.get(p.id, {})
        rows.append(PayeeRow(
            payee_id=p.id, kind=p.type, identifier=p.value_norm, msg_ids=msg_ids, amount_in_chat=case.amounts.get(p.id),
            result=get(d, "result"), rule_id=get(d, "rule_id"), reasons=list(get(d, "reasons") or []),
            next_step=display_next_step(d),
            findings=[_finding(e, d) for e in case.evidence_for(p.id)],
            voice_note=vnote, utr=pp.get("utr", "").strip(), paid_on=pp.get("paid_on", "").strip(),
            amount_paid=pp.get("amount_paid", "").strip()))
    return ReportData(
        case_id=case.case_id, generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"), claimed_firm=case.claimed_firm,
        case_result=case.case_result(), decision_source=case.bundle.source, is_stub=case.bundle.is_stub, money_sent=money_sent,
        payees=rows,
        timeline=[{"msg_id": get(m, "msg_id"), "ts": get(m, "ts"), "sender": get(m, "sender"), "kind": get(m, "kind"),
                   "text": get(m, "text")} for m in case.extraction.messages],
        cues=[{"msg_id": get(c, "msg_id"), "type": get(c, "type"), "severity": get(c, "severity"), "excerpt": get(c, "excerpt")}
              for c in case.extraction.cues],
        files=case.files, voice=[{"file_id": get(v, "file_id"), "state": get(v, "state")} for v in case.voice],
        case_findings=[_finding(e) for e in case.case_level_evidence()],
        complainant_mobile=user.get("mobile", "").strip(), debited_bank=user.get("bank", "").strip(),
        debited_account=user.get("account", "").strip(), screenshots=user.get("screenshots", "").strip())


def _finding(e, decision=None) -> dict:
    lane = get(e, "lane")
    cited = decision is not None and get(e, "evidence_id") in (get(decision, "evidence_ids") or [])
    return {"rule": get(decision, "rule_id") if cited else "not used for this result","evidence_id": get(e, "evidence_id"), "claimed": get(e, "claimed"),
            "observed": voice_adapter.observed_for_display(lane, get(e, "observed")), "source": get(e, "source"),
            "as_of": get(e, "as_of"), "limitation": get(e, "limitation"), "class": evidence_class(e), "lane": lane}
