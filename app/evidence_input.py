"""Turns what the user typed (the payee name their bank/UPI app showed) into a contract Evidence item.

Lane payee_name, class A (brief 3.2: user-run official check). Always labelled user-reported.
"""

from __future__ import annotations

from datetime import date

from .contracts import Evidence

SOURCES = ["Bank app (beneficiary name)", "UPI app (payee name before paying)", "SEBI Check"]
LIMITATION = ("Shows the name the app displayed on that date, as typed by the user. VERIQ did not contact any bank, "
              "UPI provider or SEBI and cannot authenticate it.")


def payee_name_evidence(payee_id: str, claimed_firm: str, observed_name: str, source: str, as_of: date) -> object | None:
    name = (observed_name or "").strip()
    if not name:
        return None  # missing evidence stays missing
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}")
    return Evidence(evidence_id=f"ev-{payee_id}-payee_name", payee_id=payee_id, lane="payee_name", evidence_class="A",
                    claimed=f"Payment goes to {claimed_firm}" if claimed_firm else "Payment goes to the claimed firm",
                    observed=name[:120], source=f"User-reported: {source}", as_of=as_of.isoformat(), limitation=LIMITATION)
