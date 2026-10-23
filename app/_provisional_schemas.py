"""PROVISIONAL transcription of the shared data contracts in VERIQ_Team_Brief.md section 3.3.

Owner of the real contract: Claude A (`core/schemas.py`). This file exists only so the app can run before
Claude A's schema lands. It is imported ONLY when `core.schemas` cannot be imported (see app/contracts.py).
Do not extend it; propose changes in CHANGES_REQUESTED.md.

Python cannot use `class` as an attribute name, so Evidence stores it as `evidence_class` and serialises it
as "class" (see CHANGES_REQUESTED.md, CR-C1).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

MessageKind = Literal["text", "voice", "image", "system"]
IndicatorType = Literal["upi_vpa", "bank_account", "ifsc", "phone", "sebi_reg", "url", "app_name", "firm_name"]
CueType = Literal["urgency", "fee_to_withdraw", "guaranteed_return", "otp_pin_request", "remote_access", "secrecy",
                  "authority_claim", "payee_change"]
VoiceState = Literal["flagged", "no_signal", "cant_assess"]
Lane = Literal["registration", "payee_name", "voice", "registry", "speaker"]
EvidenceClass = Literal["A", "B", "C", "D", "E"]
Result = Literal["LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "HUMAN_REVIEW", "INCONCLUSIVE", "NO_MAJOR_ISSUE"]


@dataclass(frozen=True)
class Message:
    msg_id: int
    ts: str  # ISO 8601
    sender: str
    kind: MessageKind
    text: str
    media_ref: str | None = None


@dataclass(frozen=True)
class Indicator:
    id: str
    case_id: str
    msg_id: int
    type: IndicatorType
    value_norm: str
    value_raw: str
    source: Literal["text", "voice"]
    confidence: Literal["high", "medium", "low"]
    span: tuple[int, int]


@dataclass(frozen=True)
class Cue:
    msg_id: int
    type: CueType
    severity: Literal["hard", "soft"]
    excerpt: str


@dataclass(frozen=True)
class VoiceResult:
    file_id: str
    state: VoiceState
    score: float | None
    threshold: float | None
    speech_seconds: float
    reasons: tuple[str, ...] = ()
    model_version: str = ""


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    payee_id: str
    lane: Lane
    evidence_class: EvidenceClass  # serialised as "class"
    claimed: str
    observed: str
    source: str
    as_of: str  # ISO date
    limitation: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["class"] = d.pop("evidence_class")
        return d


@dataclass(frozen=True)
class Decision:
    payee_id: str
    result: Result
    rule_id: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    next_step: str = ""
