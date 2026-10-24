"""Mistake recovery: a user flagged by mistake asks for a review; a reviewer upholds or overturns (FINALE, Claude C).

Design (deck p9 "Scammer coaches the victim"; rubric: "what a genuine user flagged by mistake goes through and how
fast they get past it"):
- The user can never clear an alert alone (a scammer could coach them to). The user explains and attaches a
  reference (the firm's SEBI-registered name, its @valid UPI handle, a bank reference); the payee is shown as
  "review requested".
- A reviewer (fraud desk / cyber cell in a pilot; a second person in the demo) upholds or overturns, with a reason.
  An overturn shows "Reviewed: explained" and the original result stays visible. It is never "safe".
- Every step is written to an audit trail: time, payee (keyed hash only, no raw identifier), original result,
  action, reason. Elapsed time from request to decision is shown.
- If the SQLite registry is on, an overturn records a reviewer rejection there, so false reports stop linking.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field

REASONS = [
    "I typed the name wrong",
    "The firm uses a different legal or trading name",
    "This is the firm's proprietor / owner",
    "Other (explain)",
]
ACCUSING = {"LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "HUMAN_REVIEW"}
_VALID = re.compile(r"^[a-z0-9._-]+@valid[a-z]+$")


def payee_hash(value_norm: str) -> str:
    """Short, non-reversible label for the audit trail (not keyed: it only avoids storing the raw identifier)."""
    return hashlib.sha256(("veriq-audit:" + value_norm).encode()).hexdigest()[:16]


def is_valid_handle(vpa: str) -> bool:
    """SEBI's '@valid' UPI handle format for registered intermediaries (format only: confirm on SEBI Check)."""
    return bool(_VALID.match((vpa or "").strip().lower()))


@dataclass
class Request:
    payee_id: str
    payee_label: str
    original_result: str
    reason: str
    note: str
    reference: str
    requested_at: float = field(default_factory=time.time)
    status: str = "review requested"  # review requested | upheld | overturned
    reviewer: str = ""
    reviewer_reason: str = ""
    decided_at: float | None = None

    def elapsed(self) -> str:
        if self.decided_at is None:
            return f"waiting {int(time.time() - self.requested_at)} s"
        return f"decided in {int(self.decided_at - self.requested_at)} s"


@dataclass
class Ledger:
    requests: dict[str, Request] = field(default_factory=dict)
    audit: list[dict] = field(default_factory=list)

    def _log(self, action: str, r: Request, **extra) -> None:
        self.audit.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, "payee": payee_hash(r.payee_label),
                           "original_result": r.original_result, "reason": r.reason, **extra})

    def request(self, payee_id: str, payee_value: str, original_result: str, reason: str, note: str,
                reference: str) -> Request:
        if original_result not in ACCUSING:
            raise ValueError("only a warning result can be sent for review")
        if reason not in REASONS:
            raise ValueError("unknown reason")
        r = Request(payee_id, payee_value, original_result, reason, note.strip()[:300], reference.strip()[:120])
        self.requests[payee_id] = r
        self._log("review requested", r, note=r.note, reference=r.reference)
        return r

    def decide(self, payee_id: str, action: str, reviewer: str, reason: str, registry=None, indicator_type="upi_vpa"):
        if action not in ("upheld", "overturned"):
            raise ValueError("action must be 'upheld' or 'overturned'")
        if not reviewer.strip() or not reason.strip():
            raise ValueError("a reviewer name and a reason are required")
        r = self.requests[payee_id]
        r.status, r.reviewer, r.reviewer_reason, r.decided_at = action, reviewer.strip()[:60], reason.strip()[:300], time.time()
        self._log(action, r, reviewer=r.reviewer, reviewer_reason=r.reviewer_reason, elapsed=r.elapsed())
        if registry is not None and hasattr(registry, "review"):
            registry.review(indicator_type, payee_value_for_registry(r), "rejected" if action == "overturned" else "confirmed",
                            r.reviewer)
        return r

    def audit_json(self) -> str:
        return json.dumps({"audit_trail": self.audit, "requests": {k: {**asdict(v), "payee_label": payee_hash(v.payee_label)}
                                                                    for k, v in self.requests.items()}}, indent=1)


def payee_value_for_registry(r: Request) -> str:
    return r.payee_label
