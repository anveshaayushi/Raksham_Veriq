"""STUB registry for v0. It holds no reports and links nothing on its own.

It answers only for the explicit synthetic fixture keys below; every other payee gets "unavailable" (not "clean"),
so a missing registry can never look like a clean history. User-entered identifiers are never added.
"""

from __future__ import annotations

from .interface import RegistryResult, is_non_attributable

# Explicit synthetic test fixtures only (fictional identifiers). value_norm -> (status, independent reporters)
FIXTURES: dict[str, tuple[str, int]] = {
    "navyug.brk@validhdfc": ("clean", 0),
    "fixture.linked@upi": ("linked", 3),
}
SOURCE = "STUB fixture table (registry/stub.py), not a real registry"


class StubRegistry:
    def lookup(self, payee_id: str, indicator_type: str, value_norm: str) -> RegistryResult:
        if is_non_attributable(indicator_type, value_norm):
            return RegistryResult(payee_id, "unavailable", 0, False, SOURCE, "payment-gateway handle: never linked")
        hit = FIXTURES.get(value_norm.lower())
        if hit is None:
            return RegistryResult(payee_id, "unavailable", 0, False, SOURCE, "no registry connected for this payee")
        status, n = hit
        return RegistryResult(payee_id, status, n, False, SOURCE, "synthetic fixture entry")
