"""Decision adapter. The app does NOT contain a decision ladder of its own.

Order:
1. Claude A's engine, if importable (ASSUMED signature, see CHANGES_REQUESTED.md CR-C5):
       rules.decide(claimed_firm=str, payees=list[Indicator], indicators=list[Indicator], cues=list[Cue],
                    evidence=list[Evidence], voice=list[VoiceResult], registry=list[RegistryResult]) -> list[Decision]
2. A demo fixture's stub decisions, only if every input still equals the fixture's inputs.
3. Otherwise a STUB: INCONCLUSIVE per payee with rule_id "STUB-NO-ENGINE". Never NO_MAJOR_ISSUE.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import Decision

STUB_RULE = "STUB-NO-ENGINE"
STUB_NEXT = "Don't pay yet. Check who receives the money in your own bank or UPI app, and contact the firm through a number or website you find yourself."


@dataclass
class DecisionBundle:
    decisions: list
    source: str
    is_stub: bool
    notes: list[str] = field(default_factory=list)


def decide(*, claimed_firm: str, payees: list, indicators: list, cues: list, evidence: list, voice: list, registry: list,
           fixture: dict | None = None, fixture_inputs_match: bool = False) -> DecisionBundle:
    notes: list[str] = []
    try:
        import rules  # type: ignore  # Claude A

        if hasattr(rules, "decide"):
            out = rules.decide(claimed_firm=claimed_firm, payees=payees, indicators=indicators, cues=cues, evidence=evidence,
                               voice=voice, registry=registry)
            return DecisionBundle(list(out), "rules/ (Claude A)", False)
    except ImportError:
        pass
    except Exception as e:
        notes.append(f"Claude A's rules raised {type(e).__name__}; showing stub output instead. See CHANGES_REQUESTED.md.")

    if fixture and fixture_inputs_match:
        by_value = {p.value_norm: p.id for p in payees}
        ds = []
        for d in fixture["stub_decisions"]:
            pid = by_value.get(d["payee"])
            if pid is None:
                continue
            ev_ids = tuple(e.evidence_id for e in evidence if e.payee_id == pid)
            ds.append(Decision(payee_id=pid, result=d["result"], rule_id=d["rule_id"], reasons=tuple(d["reasons"]),
                               evidence_ids=ev_ids, next_step=d["next_step"]))
        if len(ds) == len(payees):
            notes.append("These results are the demo fixture's expected values, typed in by hand. No rules engine ran.")
            return DecisionBundle(ds, f"STUB: provisional demo fixture {fixture['id']}", True, notes)
        notes.append("The demo fixture does not cover every payee; falling back to the stub.")
    elif fixture:
        notes.append("You changed the demo inputs, so the fixture's expected results no longer apply.")

    ds = []
    for p in payees:
        ev_ids = tuple(e.evidence_id for e in evidence if e.payee_id == p.id)
        reasons = ["The decision engine is not connected in this v0 skeleton, so no result was computed for this payee."]
        if not ev_ids:
            reasons.append("No payee name from your bank or UPI app was entered (missing evidence).")
        ds.append(Decision(payee_id=p.id, result="INCONCLUSIVE", rule_id=STUB_RULE, reasons=tuple(reasons),
                           evidence_ids=ev_ids, next_step=STUB_NEXT))
    return DecisionBundle(ds, "STUB in app/adapters/decide.py (Claude A's rules not found)", True, notes)
