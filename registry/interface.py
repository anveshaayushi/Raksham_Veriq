"""Registry interface (brief section 8). v0 ships only a stub behind this interface; the SQLite registry comes later.

Plain idea: "have other people reported this payee before?" answered without sharing anyone's chat.
Technical: indicators are pseudonymised with keyed HMAC-SHA256, namespaced by type, using a server-held secret.
This is pseudonymisation, not anonymity: whoever holds the secret can test a guess.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Literal, Protocol

Status = Literal["clean", "linked", "unavailable"]

# Non-attributable classes are never linked (brief section 8): gateway / aggregator / bank-owned handles.
NON_ATTRIBUTABLE_SUFFIXES = ("@razorpay", "@cashfree", "@payu", "@billdesk", "@ccavenue", "@juspay", "@easebuzz")
LINK_MIN_INDEPENDENT_REPORTERS = 2
DECAY_DAYS = 180


@dataclass(frozen=True)
class RegistryResult:
    payee_id: str
    status: Status
    independent_reporters: int
    reviewer_confirmed: bool
    source: str  # e.g. "STUB fixture table" or "SQLite registry"
    note: str = ""


class Registry(Protocol):
    def lookup(self, payee_id: str, indicator_type: str, value_norm: str) -> RegistryResult: ...


def hmac_indicator(secret: bytes, indicator_type: str, value_norm: str) -> str:
    """Keyed, type-namespaced pseudonym for an indicator. Refuses to run without a real secret."""
    if not secret or len(secret) < 16:
        raise ValueError("registry secret must be at least 16 bytes")
    msg = f"{indicator_type}\x1f{value_norm.strip().lower()}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def is_non_attributable(indicator_type: str, value_norm: str) -> bool:
    v = value_norm.lower()
    return indicator_type == "upi_vpa" and v.endswith(NON_ATTRIBUTABLE_SUFFIXES)
