"""Assemble a case from inputs, with no Streamlit dependency (so it is testable).

chat text -> extraction (adapter) -> payees -> user-reported evidence -> voice (adapter) -> registry (stub)
-> decisions (adapter) -> report data. The app only displays what this returns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from registry.stub import StubRegistry
from report.build import PayeeRow, ReportData

from .adapters import decide as decide_adapter
from .adapters import extract as extract_adapter
from .adapters import voice as voice_adapter
from .contracts import VoiceResult, case_result, evidence_class, get
from .evidence_input import payee_name_evidence
from .intake import safe_name
from .next_steps import display_next_step, with_money_sent

DEMO_DIR = Path(__file__).resolve().parent / "demo"


def load_demo(sid: str) -> dict:
    if sid not in ("A", "B", "C"):
        raise ValueError("unknown demo scenario")
    return json.loads((DEMO_DIR / f"scenario_{sid}.json").read_text(encoding="utf-8"))


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
    fixture_id: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def decisions(self) -> list:
        return self.bundle.decisions

    def result_for(self, payee_id: str):
        return next((d for d in self.decisions if get(d, "payee_id") == payee_id), None)

    def case_result(self) -> str | None:
        return case_result(self.decisions)


def extract(case_id: str, chat_text: str, transcripts: dict | None = None) -> extract_adapter.Extraction:
    return extract_adapter.run(chat_text, case_id, transcripts)


def build_case(*, case_id: str, chat_text: str, claimed_firm: str, checks: dict[str, UserCheck],
               audio: dict[str, bytes] | None = None, files: list[dict] | None = None, transcripts: dict | None = None,
               fixture: dict | None = None) -> Case:
    ex = extract(case_id, chat_text, transcripts)
    payees = extract_adapter.payees(ex.indicators)
    evidence = []
    for p in payees:
        c = checks.get(p.value_norm)
        if c is not None:
            ev = payee_name_evidence(p.id, claimed_firm, c.observed_name, c.source, c.as_of)
            if ev is not None:
                evidence.append(ev)

    # voice: one result per voice message
    voice, voice_stub = [], False
    audio = {safe_name(k): v for k, v in (audio or {}).items()}
    fixture_voice = {v["file_id"]: v for v in (fixture or {}).get("stub_voice", [])}
    for m in ex.messages:
        if get(m, "kind") != "voice":
            continue
        ref = get(m, "media_ref") or f"msg{get(m, 'msg_id')}"
        if ref in fixture_voice:
            fv = fixture_voice[ref]
            voice.append(VoiceResult(file_id=ref, state=fv["state"], score=fv["score"], threshold=fv["threshold"],
                                     speech_seconds=fv["speech_seconds"], reasons=tuple(fv["reasons"]),
                                     model_version="stub-fixture (no detector ran)"))
            voice_stub = True
        elif safe_name(ref) in audio:
            vr, is_stub = voice_adapter.analyse(ref, audio[safe_name(ref)], ref)
            voice.append(vr)
            voice_stub = voice_stub or is_stub
        else:
            voice.append(VoiceResult(file_id=ref, state="cant_assess", score=None, threshold=None, speech_seconds=0.0,
                                     reasons=("The voice note is mentioned in the chat but the file was not uploaded.",),
                                     model_version="none"))

    reg = StubRegistry()
    registry = [reg.lookup(p.id, p.type, p.value_norm) for p in payees]

    match = False
    if fixture:
        fx_checks = {k: (v[0], v[1]) for k, v in fixture.get("checks", {}).items()}
        given = {k: (c.observed_name.strip(), c.source) for k, c in checks.items() if c.observed_name.strip()}
        match = chat_text == fixture["chat"] and claimed_firm.strip() == fixture["claimed_firm"] and given == fx_checks
    bundle = decide_adapter.decide(claimed_firm=claimed_firm, payees=payees, indicators=ex.indicators, cues=ex.cues,
                                   evidence=evidence, voice=voice, registry=registry, fixture=fixture,
                                   fixture_inputs_match=match)
    return Case(case_id, claimed_firm, ex, payees, evidence, voice, voice_stub, registry, bundle, files or [],
                fixture["id"] if fixture else None)


def report_data(case: Case, *, money_sent: bool, user: dict[str, str] | None = None,
                per_payee: dict[str, dict[str, str]] | None = None) -> ReportData:
    user = user or {}
    per_payee = per_payee or {}
    msgs = {get(m, "msg_id"): m for m in case.extraction.messages}
    voice_by_ref = {get(v, "file_id"): v for v in case.voice}
    rows = []
    for p in case.payees:
        d = with_money_sent(case.result_for(p.id), money_sent)
        evs = [e for e in case.evidence if get(e, "payee_id") == p.id]
        msg_ids = sorted({get(i, "msg_id") for i in case.extraction.indicators if i.value_norm == p.value_norm})
        first = msgs.get(msg_ids[0]) if msg_ids else None
        vnote = None
        if first is not None and get(first, "kind") == "voice":
            v = voice_by_ref.get(get(first, "media_ref"))
            vnote = f"payee taken from a voice-note transcript; voice check: {get(v, 'state')} ({'; '.join(get(v, 'reasons') or [])})" if v else None
        pp = per_payee.get(p.id, {})
        rows.append(PayeeRow(
            payee_id=p.id, kind=p.type, identifier=p.value_norm, msg_ids=msg_ids,
            amount_in_chat=extract_adapter.amount_in(get(first, "text") if first is not None else ""),
            result=get(d, "result"), rule_id=get(d, "rule_id"), reasons=list(get(d, "reasons") or []),
            next_step=display_next_step(d),
            findings=[{"claimed": get(e, "claimed"), "observed": get(e, "observed"), "source": get(e, "source"),
                       "as_of": get(e, "as_of"), "limitation": get(e, "limitation"), "class": evidence_class(e),
                       "lane": get(e, "lane")} for e in evs],
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
        complainant_mobile=user.get("mobile", "").strip(), debited_bank=user.get("bank", "").strip(),
        debited_account=user.get("account", "").strip(), screenshots=user.get("screenshots", "").strip())
