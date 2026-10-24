"""Decision adapter. The app does NOT contain a decision ladder of its own.

1. Claude A's engine when `rules.decide` exists (ASSUMED signature, CR-C5):
       rules.decide(claimed_firm=str, payees=list[Indicator], indicators=list[Indicator], cues=list[Cue],
                    evidence=list[Evidence], voice=list[VoiceResult], registry=list[RegistryResult]) -> list[Decision]
2. Otherwise a STUB: INCONCLUSIVE (rule_id INCONCL, the contract's id) per payee, with a reason saying no engine ran.
   Never NO_MAJOR_ISSUE. Demo scenarios do not come through here: they use Claude A's golden fixtures (app/case.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import Decision

STUB_REASON = "The decision engine is not built yet (Claude A's rules/), so no result was computed for this payee."
STUB_NEXT = ("Don't pay yet. Check who receives the money in your own bank or UPI app, and contact the firm through a number "
             "or website you find yourself. If money was sent, call 1930.")


@dataclass
class DecisionBundle:
    decisions: list
    source: str
    is_stub: bool
    notes: list[str] = field(default_factory=list)


def decide(*, claimed_firm: str, payees: list, indicators: list, cues: list, evidence: list, voice: list,
           registry: list) -> DecisionBundle:
    notes: list[str] = []
    try:
        import rules  # type: ignore  # Claude A

        if hasattr(rules, "decide"):
            out = rules.decide(claimed_firm=claimed_firm, payees=payees, indicators=indicators, cues=cues, evidence=evidence,
                               voice=voice, registry=registry)
            return DecisionBundle(list(out), "rules/ decision engine (FINALE)", False)
    except ImportError:
        pass
    except Exception as e:
        notes.append(f"Claude A's rules raised {type(e).__name__}; showing the stub instead. See CHANGES_REQUESTED.md.")
    ds = []
    for p in payees:
        ev_ids = [e.evidence_id for e in evidence if e.payee_id == p.id]
        reasons = [STUB_REASON]
        if not any(getattr(e, "lane", "") == "payee_name" for e in evidence if e.payee_id == p.id):
            reasons.append("No payee name from your bank or UPI app was entered (missing evidence).")
        ds.append(Decision(payee_id=p.id, result="INCONCLUSIVE", rule_id="INCONCL", reasons=reasons, evidence_ids=ev_ids,
                           next_step=STUB_NEXT))
    return DecisionBundle(ds, "STUB in app/adapters/decide.py (Claude A's rules/ is empty)", True, notes)
