"""Next-step wording and the money-already-sent toggle (brief section 6, invariants 5 and 6).

The toggle changes ONLY `next_step`; result, rule_id, reasons and evidence_ids are copied unchanged.
"""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import Any

from .contracts import get

NOT_A_GUARANTEE = "This is not a guarantee."
STANDING_LINE = "VERIQ files no complaints, blocks nothing and contacts no one."

MONEY_SENT_STEP = (
    "Money already sent: call 1930 now (National Cyber Crime Helpline) or report at cybercrime.gov.in. "
    "Have the UTR (12-digit transaction ID), date, amount and the recipient UPI ID or account ready; the filing sheet "
    "below lists them. Also tell your own bank. The sooner you report, the better the chance of a freeze."
)


def money_sent_step(result: str | None) -> str:
    """The 1930 next step; keeps "This is not a guarantee." for NO_MAJOR_ISSUE (golden variant, invariant 5)."""
    return f"{MONEY_SENT_STEP} {NOT_A_GUARANTEE}" if result == "NO_MAJOR_ISSUE" else MONEY_SENT_STEP


def with_money_sent(decision: Any, money_sent: bool) -> Any:
    """Return the decision with next_step replaced by the 1930 flow when money was already sent."""
    if not money_sent:
        return decision
    step = money_sent_step(get(decision, "result"))
    if isinstance(decision, dict):
        return {**decision, "next_step": step}
    if is_dataclass(decision):
        return replace(decision, next_step=step)
    if hasattr(decision, "model_copy"):
        return decision.model_copy(update={"next_step": step})
    raise TypeError(f"unsupported decision type {type(decision).__name__}")


def disclaimer_for(result: str | None) -> str | None:
    """NO_MAJOR_ISSUE must always carry the not-a-guarantee line, whatever the engine wrote."""
    return NOT_A_GUARANTEE if result == "NO_MAJOR_ISSUE" else None


def display_next_step(decision: Any) -> str:
    step = get(decision, "next_step") or "Don't pay yet. Verify the recipient through the firm's official contact."
    extra = disclaimer_for(get(decision, "result"))
    if extra and extra not in step:
        step = f"{step} {extra}"
    return step


PLAIN_LABEL = {
    "LINKED": "Reported before by other people",
    "NAME_DISCREPANCY": "Payee name doesn't match the firm",
    "REGISTRATION_CONFLICT": "Registration claim conflicts",
    "HUMAN_REVIEW": "Needs a human to review",
    "INCONCLUSIVE": "Not enough evidence",
    "NO_MAJOR_ISSUE": "No major issue found",
}
