"""Single import point for the shared contracts.

Uses Claude A's `core/schemas.py` when it exists; otherwise falls back to the provisional transcription of the
brief (section 3.3). The app shows which one is active, so a fallback is never mistaken for the real contract.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from . import _provisional_schemas as _prov

_NAMES = ("Message", "Indicator", "Cue", "VoiceResult", "Evidence", "Decision")


def _load() -> tuple[dict, dict]:
    """Take each contract type from core/schemas.py if it defines it (A owns it; B may have drafted part of it),
    otherwise from the provisional copy. Returns (types, origin per name)."""
    try:
        import core.schemas as real  # type: ignore
    except ImportError:
        real = None
    types, origin = {}, {}
    for n in _NAMES:
        if real is not None and hasattr(real, n):
            types[n], origin[n] = getattr(real, n), "core.schemas"
        else:
            types[n], origin[n] = getattr(_prov, n), "provisional"
    return types, origin


_TYPES, ORIGIN = _load()
Message, Indicator, Cue, VoiceResult, Evidence, Decision = (_TYPES[n] for n in _NAMES)
PROVISIONAL = any(v == "provisional" for v in ORIGIN.values())
if all(v == "core.schemas" for v in ORIGIN.values()):
    SCHEMA_SOURCE = "core.schemas (shared contract)"
elif all(v == "provisional" for v in ORIGIN.values()):
    SCHEMA_SOURCE = "PROVISIONAL copy of brief section 3.3 (core/schemas.py not found)"
else:
    SCHEMA_SOURCE = ("core.schemas for " + ", ".join(n for n in _NAMES if ORIGIN[n] == "core.schemas")
                     + "; PROVISIONAL for " + ", ".join(n for n in _NAMES if ORIGIN[n] == "provisional"))

__all__ = ["Cue", "Decision", "Evidence", "Indicator", "Message", "VoiceResult", "SCHEMA_SOURCE", "PROVISIONAL", "ORIGIN",
           "get", "evidence_class", "to_dict", "RESULT_RANK", "case_result"]

# Brief section 6: R1 highest. The case result is the highest-ranked payee result.
RESULT_RANK = ["LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "HUMAN_REVIEW", "INCONCLUSIVE", "NO_MAJOR_ISSUE"]


def get(obj: Any, name: str, default: Any = None) -> Any:
    """Read a contract field from a dataclass, a pydantic model or a dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def evidence_class(ev: Any) -> str | None:
    for name in ("evidence_class", "class_", "klass", "class"):
        v = get(ev, name)
        if v is not None:
            return v
    return None


def to_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"cannot serialise {type(obj).__name__}")


def case_result(decisions: list[Any]) -> str | None:
    """Worst (highest-ranked) payee result, per brief section 6. None if there are no payees."""
    results = [get(d, "result") for d in decisions]
    for r in RESULT_RANK:
        if r in results:
            return r
    return None
