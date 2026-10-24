"""Decision rules: one answer per payee; the case takes the worst one (brief section 6, deck p6).

FINALE, 24 Oct 2026. Claude A's ladder, ported onto the shared contract by Claude C at the team's request
(A's delivery used ResultCategory / Decision(category=...), which core/schemas.py does not define). CR-C13.

decide(*, claimed_firm, payees, indicators, cues, evidence, voice, registry) -> list[Decision]
case_evidence(...) -> list[Evidence]     registration, voice and registry evidence around the user's name checks
case_result(decisions) -> Decision        worst payee (ties: first in the chat)

Ladder, first rule that applies wins (no weights, no scores):
 1 LINKED                 registry status "linked" (>= 2 independent reporters or a reviewer)       class C
 2 NAME_DISCREPANCY       user-run app check (class A) shows a business name unrelated to the firm   class A
 3 REGISTRATION_CONFLICT  quoted SEBI number not in the dated list, or listed to another entity      class B
 4 HUMAN_REVIEW           a voice note is flagged, or two user checks for one payee disagree          class E / A
 5 INCONCLUSIVE           no usable class A check, name unverified, voice can't be assessed, or a hard cue
 6 NO_MAJOR_ISSUE         class A name matches and nothing above applies; always "This is not a guarantee."
Class D (chat cues) and class E (voice) can only push towards caution; they never clear a payee.
"""

from __future__ import annotations

import re

from core.schemas import CASE_LEVEL_PAYEE_ID, RESULT_RANK, RESULT_TO_RULE, Decision, Evidence
from match import match_names

from . import sebi
from .templates import NEXT_STEP

__all__ = ["decide", "case_evidence", "case_result", "NEXT_STEP"]


def _g(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _voice_state(observed: str) -> str | None:
    m = re.match(r"\s*(flagged|no_signal|cant_assess)\b", observed or "")
    return m.group(1) if m else None


def _decision(payee_id: str, result: str, reasons: list[str], evidence_ids: list[str]) -> Decision:
    return Decision(payee_id=payee_id, result=result, rule_id=RESULT_TO_RULE[result], reasons=reasons,
                    evidence_ids=evidence_ids, next_step=NEXT_STEP[result])


def decide(*, claimed_firm: str, payees: list, indicators: list, cues: list, evidence: list, voice: list,
           registry: list) -> list[Decision]:
    case_ev = [e for e in evidence if e.payee_id == CASE_LEVEL_PAYEE_ID]
    reg_ev = next((e for e in case_ev if e.lane == "registration"), None)
    reg_state, reg_entity = sebi.read_registration(reg_ev.observed) if reg_ev else ("none", None)
    reg_conflict = reg_state == "not_listed" or (
        reg_state == "listed" and match_names(claimed_firm, reg_entity or "")[0] == "discrepancy")
    hard = [c for c in cues if _g(c, "severity") == "hard"]
    registry_by_payee = {_g(r, "payee_id"): r for r in registry or []}
    reg_quote = next((i.value_norm for i in indicators if i.type == "sebi_reg"), None)

    out: list[Decision] = []
    for p in payees:
        own = [e for e in evidence if e.payee_id == p.id]
        names = [e for e in own if e.lane == "payee_name" and e.class_ == "A"]
        verdicts = [(e, *match_names(claimed_firm, e.observed)) for e in names]
        voice_ev = [e for e in own + case_ev if e.lane == "voice"]
        registry_ev = next((e for e in own if e.lane == "registry"), None)
        rr = registry_by_payee.get(p.id)
        rstatus = _g(rr, "status") if rr is not None else None
        label = p.value_raw

        voice_notes = []
        for e in voice_ev:
            st = _voice_state(e.observed)
            if st == "no_signal":
                voice_notes.append("Voice note: no_signal. Does not clear or accuse.")
            elif st == "cant_assess":
                why = e.observed.split(":", 1)[1].split("(")[0].strip() if ":" in e.observed else "not assessable"
                voice_notes.append(f"Voice note: can't assess ({why}).")
            elif st == "flagged":
                voice_notes.append("Voice note: flagged by the detector (a review cue, not proof).")
        outranked = []
        if reg_conflict:
            outranked.append(f"Also present but outranked: SEBI number {reg_quote or '(quoted)'} "
                             f"{'not in the dated snapshot' if reg_state == 'not_listed' else 'listed to another entity'}"
                             " (REG_CONFLICT).")

        # 1 LINKED
        if rstatus == "linked" and registry_ev is not None:
            out.append(_decision(p.id, "LINKED",
                                 [f"Registry: {registry_ev.observed} (class C). Pseudonymised reports, not a conviction."]
                                 + voice_notes, [registry_ev.evidence_id]))
            continue
        # 2 NAME_DISCREPANCY
        disc = [(e, why) for e, v, why in verdicts if v == "discrepancy"]
        if disc and not any(v == "match" for _, v, _ in verdicts):
            e, why = disc[0]
            out.append(_decision(p.id, "NAME_DISCREPANCY",
                                 [f"Class A (user-reported): app shows '{e.observed}'; no shared distinctive word with "
                                  f"claimed '{claimed_firm}'."] + outranked + voice_notes, [e.evidence_id for e, _ in disc]))
            continue
        # 3 REGISTRATION_CONFLICT
        if reg_conflict and reg_ev is not None:
            what = "is not in the dated snapshot" if reg_state == "not_listed" else f"is listed to '{reg_entity}'"
            out.append(_decision(p.id, "REGISTRATION_CONFLICT",
                                 [f"Class B: SEBI number {reg_quote or '(quoted)'} {what}, but the chat claims "
                                  f"'{claimed_firm}'."] + voice_notes, [reg_ev.evidence_id]))
            continue
        # 4 HUMAN_REVIEW
        flagged = [e for e in voice_ev if _voice_state(e.observed) == "flagged"]
        disagree = len({v for _, v, _ in verdicts if v in ("match", "discrepancy")}) > 1
        if flagged or disagree:
            reasons = []
            if flagged:
                reasons.append("A voice note was flagged by the detector. That is a cue for a person to review, "
                               "not proof of a fake voice.")
            if disagree:
                reasons.append("Two name checks for this payee disagree.")
            out.append(_decision(p.id, "HUMAN_REVIEW", reasons,
                                 [e.evidence_id for e in flagged] + ([e.evidence_id for e in names] if disagree else [])))
            continue
        # 5 INCONCLUSIVE
        unverified = [(e, why) for e, v, why in verdicts if v == "unverified"]
        cant = [e for e in voice_ev if _voice_state(e.observed) == "cant_assess"]
        matched = [e for e, v, _ in verdicts if v == "match"]
        if not matched or cant or hard:
            reasons, cited = [], []
            if not names:
                reasons.append(f"No class A evidence for {label}: the user has not run a bank/UPI-app name check.")
            for e, why in unverified:
                reasons.append(f"Name check unverified: app shows '{e.observed}': {why}.")
                cited.append(e.evidence_id)
            for e in cant:
                cited.append(e.evidence_id)
            reasons += [n for n in voice_notes if n.startswith("Voice note: can't")]
            for c in hard:
                reasons.append(f"Hard cue: {_g(c, 'type')} in msg {_g(c, 'msg_id')}.")
            if rstatus == "unavailable":
                reasons.append("Registry: unavailable (not counted as clean).")
            out.append(_decision(p.id, "INCONCLUSIVE", reasons, cited))
            continue
        # 6 NO_MAJOR_ISSUE
        cited = [matched[0].evidence_id]
        reasons = [f"Class A (user-reported): app shows '{matched[0].observed}', which shares distinctive words with "
                   "the claimed firm."]
        if reg_ev is not None and reg_state == "listed":
            cited.append(reg_ev.evidence_id)
            reasons.append(f"SEBI number {reg_quote or ''} is in the dated snapshot under a matching entity (class B; "
                           "not verification of the payee).".replace("  ", " "))
        if registry_ev is not None and rstatus == "clean":
            cited.append(registry_ev.evidence_id)
        reasons.append(("Registry: no reports. " if rstatus == "clean" else "Registry: not checked. ")
                       + "No hard pressure cues. No voice flag.")
        out.append(_decision(p.id, "NO_MAJOR_ISSUE", reasons, cited))
    return out


def case_result(decisions: list) -> Decision | None:
    """Worst payee wins; ties go to the payee that appears first."""
    return min(decisions, key=lambda d: RESULT_RANK[d.result]) if decisions else None


# --------------------------------------------------------------------------------------------- evidence builder ----
def _next_id(case_id: str, evidence: list) -> int:
    nums = [int(m.group(1)) for e in evidence if (m := re.search(r"-E(\d+)$", e.evidence_id))]
    return max(nums, default=0) + 1


def case_evidence(*, case_id: str, claimed_firm: str, messages: list, indicators: list, payees: list,
                  payee_name_evidence: list, voice: list, registry: list, as_of: str,
                  snapshot_path=sebi.DEFAULT_SNAPSHOT) -> list[Evidence]:
    """The user's name checks (class A, built by the app) plus registration (B), voice (E) and registry (C)."""
    ev = list(payee_name_evidence)
    n = _next_id(case_id, ev)

    def eid() -> str:
        nonlocal n
        n += 1
        return f"{case_id}-E{n - 1}"

    reg = next((i for i in indicators if i.type == "sebi_reg"), None)
    if reg is not None:
        try:
            snap = sebi.load_snapshot(snapshot_path)
            label = f"dated public-list snapshot ({snap['source'][:60]})" if snap["source"] else "dated public-list snapshot"
            ev.append(sebi.registration_evidence(eid(), reg.value_norm, claimed_firm, reg.msg_id, snap, label,
                                                 snap["as_of"] or as_of))
        except (OSError, ValueError, KeyError):
            pass  # no snapshot: no registration evidence (missing is not a match)

    msgs = {m.msg_id: m for m in messages}
    for v in voice or []:
        msg = next((m for m in messages if m.kind == "voice" and m.media_ref == _g(v, "file_id")), None)
        payee = next((p for p in payees if msg is not None and p.msg_id == msg.msg_id), None)
        state, mv = _g(v, "state"), str(_g(v, "model_version", ""))
        stub = "stub" in mv.lower() or _g(v, "threshold") is None
        if state == "cant_assess":
            why = "; ".join(_g(v, "reasons") or []) or "not assessable"
            observed = f"cant_assess: {why.replace('_', ' ')}"
        elif stub:
            observed = f"{state} (stub value, not a measurement)"
        else:
            observed = f"{state} (score {_g(v, 'score'):.2f} vs calibrated threshold {_g(v, 'threshold'):.2f})"
        limitation = {"flagged": "A flag is a cue for review, not proof the voice is synthetic.",
                      "no_signal": "A no_signal result does not mean the voice is genuine and never clears a payee.",
                      "cant_assess": "Can't assess means no opinion either way. It is not a clearance."}[state]
        ev.append(Evidence(evidence_id=eid(), payee_id=payee.id if payee else CASE_LEVEL_PAYEE_ID, lane="voice",
                           class_="E", claimed=f"voice note msg {msg.msg_id if msg else '?'} ({_g(v, 'file_id')})",
                           observed=observed, source=("voice detector STUB" if stub else f"voice detector {mv}"),
                           as_of=as_of, limitation=limitation))
    del msgs

    for p in payees:
        r = next((x for x in registry or [] if _g(x, "payee_id") == p.id), None)
        if r is None:
            continue
        st = _g(r, "status")
        observed = {"linked": f"linked: {_g(r, 'note') or 'independent reports'}",
                    "clean": "no matching report" + (" (stub)" if "stub" in str(_g(r, "source", "")).lower() else ""),
                    "unavailable": f"registry unavailable: {_g(r, 'note') or 'no registry'}"}.get(st, st)
        ev.append(Evidence(evidence_id=eid(), payee_id=p.id, lane="registry", class_="C",
                           claimed=f"payee {p.value_raw}", observed=observed, source=str(_g(r, "source", "registry")),
                           as_of=as_of, limitation="Absence from the registry means nobody has reported it here, not "
                                                   "that it is safe. Reports are pseudonymised, not proof."))
    return ev
