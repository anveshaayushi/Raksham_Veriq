"""Registration check against a dated, local snapshot of the public SEBI list (evidence class B, lane registration).

FINALE, 24 Oct 2026. Claude A's SEBI check, ported onto the shared contract by Claude C (CR-C13).
The snapshot in fixtures/reference/ is SYNTHETIC (DEMO-marked numbers), not the real SEBI list.

Observed text uses two fixed forms that rules.decide reads back:
    "<REG> not present in the snapshot"
    "Listed as '<entity>' in the snapshot"
"""

from __future__ import annotations

import json
from pathlib import Path

from core.schemas import CASE_LEVEL_PAYEE_ID, Evidence

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "reference" / "sebi_snapshot_synthetic.json"
NOT_PRESENT = "not present in the snapshot"


def load_snapshot(path: str | Path = DEFAULT_SNAPSHOT) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"as_of": data.get("as_of", ""), "source": data.get("source", ""),
            "by_reg": {e["reg_no"].strip().upper(): e for e in data.get("entries", [])}}


def registration_evidence(evidence_id: str, reg_no: str, claimed_firm: str, msg_id: int, snapshot: dict,
                          snapshot_label: str, as_of: str) -> Evidence:
    reg = reg_no.strip().upper()
    hit = snapshot["by_reg"].get(reg)
    claimed = f"SEBI reg {reg} quoted for {claimed_firm} (msg {msg_id})"
    if hit is None:
        return Evidence(evidence_id=evidence_id, payee_id=CASE_LEVEL_PAYEE_ID, lane="registration", class_="B",
                        claimed=claimed, observed=f"{reg} {NOT_PRESENT}", source=snapshot_label, as_of=as_of,
                        limitation="Absence from a local, dated snapshot can mean the snapshot is incomplete or out "
                                   "of date. Not verification of any payee.")
    return Evidence(evidence_id=evidence_id, payee_id=CASE_LEVEL_PAYEE_ID, lane="registration", class_="B",
                    claimed=claimed, observed=f"Listed as '{hit['entity']}' in the snapshot", source=snapshot_label,
                    as_of=as_of, limitation="A listing does not show who owns a UPI ID or account. Not verification "
                                            "of the payee.")


def read_registration(observed: str) -> tuple[str, str | None]:
    """('not_listed', None) | ('listed', entity) | ('unknown', None) from an Evidence.observed string."""
    if NOT_PRESENT in observed:
        return "not_listed", None
    if observed.startswith("Listed as '") and "'" in observed[11:]:
        return "listed", observed[11:observed.index("'", 11)]
    return "unknown", None
