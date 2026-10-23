"""VERIQ shared data contracts.

Source of truth: team brief section 3.3 plus section 19 (audio/image only; video
is deliberately excluded from this build, see CHANGES_REQUESTED.md CR-1).

PLAIN WORDS: these are the "shapes" of the data that Claude A (rules), Claude B
(voice) and Claude C (app) pass to each other. If everyone sticks to these
shapes, the three parts plug together. Each shape checks itself when it is
created, so a wrong value fails loudly instead of silently reaching the UI.

TECHNICAL: frozen stdlib dataclasses (no third-party dependency, works offline),
strict `from_dict` (unknown or missing keys are rejected), `to_dict` produces the
exact JSON field names of the brief. Python reserved word `class` is stored as
`class_` and serialised as "class" (CR-2).

Anything NOT in the brief's contract is in the PROVISIONAL section at the bottom
and is tracked in CHANGES_REQUESTED.md. Do not rely on provisional types
without reading that file.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional

SCHEMA_VERSION = "0.1.0-c0"

# --------------------------------------------------------------------------
# Enumerations (exactly as in brief 3.3 / 6 / 19)
# --------------------------------------------------------------------------
MESSAGE_KINDS = ("text", "voice", "image", "system")  # no "video": out of scope
INDICATOR_TYPES = (
    "upi_vpa", "bank_account", "ifsc", "phone", "sebi_reg", "url", "app_name", "firm_name",
)
INDICATOR_SOURCES = ("text", "voice")
PROVISIONAL_INDICATOR_SOURCES = ("image",)  # OCR / QR on images, class D (CR-3)
CONFIDENCES = ("high", "medium", "low")
CUE_TYPES = (
    "urgency", "fee_to_withdraw", "guaranteed_return", "otp_pin_request",
    "remote_access", "secrecy", "authority_claim", "payee_change",
)
CUE_SEVERITIES = ("hard", "soft")
# Guidance only (not enforced): extractor may downgrade e.g. a negated phrase.
DEFAULT_CUE_SEVERITY = {
    "urgency": "soft", "authority_claim": "soft", "payee_change": "soft",
    "fee_to_withdraw": "hard", "guaranteed_return": "hard", "secrecy": "hard",
    "otp_pin_request": "hard", "remote_access": "hard",
}
VOICE_STATES = ("flagged", "no_signal", "cant_assess")
MODALITIES = ("audio", "image")  # brief allows "video"; excluded here (CR-1)
EVIDENCE_LANES = ("registration", "payee_name", "voice", "registry", "speaker")
EVIDENCE_CLASSES = ("A", "B", "C", "D", "E")
DECISION_RESULTS = (
    "LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT",
    "HUMAN_REVIEW", "INCONCLUSIVE", "NO_MAJOR_ISSUE",
)
RULE_IDS = ("LINKED", "NAME_DISC", "REG_CONFLICT", "REVIEW", "INCONCL", "CLEAR")
# Ladder rank, brief section 6. Lower number = more severe = wins.
RESULT_RANK = {
    "LINKED": 1, "NAME_DISCREPANCY": 2, "REGISTRATION_CONFLICT": 3,
    "HUMAN_REVIEW": 4, "INCONCLUSIVE": 5, "NO_MAJOR_ISSUE": 6,
}
RESULT_TO_RULE = {
    "LINKED": "LINKED", "NAME_DISCREPANCY": "NAME_DISC",
    "REGISTRATION_CONFLICT": "REG_CONFLICT", "HUMAN_REVIEW": "REVIEW",
    "INCONCLUSIVE": "INCONCL", "NO_MAJOR_ISSUE": "CLEAR",
}
CASE_LEVEL_PAYEE_ID = "CASE"  # evidence that applies to every payee (CR-4)
NOT_A_GUARANTEE = "This is not a guarantee."  # invariant 5


class SchemaError(ValueError):
    """Raised when data does not satisfy a VERIQ contract."""


# --------------------------------------------------------------------------
# Small validation helpers
# --------------------------------------------------------------------------
def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _str(name: str, v: Any, nonempty: bool = True) -> None:
    _check(isinstance(v, str), f"{name} must be str, got {type(v).__name__}")
    if nonempty:
        _check(v.strip() != "", f"{name} must not be empty")


def _enum(name: str, v: Any, allowed) -> None:
    _check(v in allowed, f"{name}={v!r} not one of {tuple(allowed)}")


def _iso_dt(name: str, v: Any) -> None:
    _str(name, v)
    try:
        datetime.fromisoformat(v)
    except ValueError as e:
        raise SchemaError(f"{name}={v!r} is not ISO8601") from e


def _iso_date(name: str, v: Any) -> None:
    _str(name, v)
    try:
        date.fromisoformat(v)
    except ValueError as e:
        raise SchemaError(f"{name}={v!r} is not an ISO date (YYYY-MM-DD)") from e


def _opt_num(name: str, v: Any) -> None:
    _check(v is None or _is_num(v), f"{name} must be number or null")


def _str_list(name: str, v: Any) -> None:
    _check(isinstance(v, list) and all(isinstance(x, str) for x in v), f"{name} must be list[str]")


def _span(name: str, v: Any) -> None:
    _check(
        isinstance(v, list) and len(v) == 2 and all(_is_int(x) for x in v),
        f"{name} must be [int,int]",
    )
    _check(0 <= v[0] < v[1], f"{name}={v} must satisfy 0 <= start < end")


def _plain(v: Any) -> Any:
    if is_dataclass(v) and hasattr(v, "to_dict"):
        return v.to_dict()
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v


class _Contract:
    """Shared (de)serialisation. Subclasses are frozen dataclasses."""

    _ALIASES: ClassVar[Dict[str, str]] = {}  # python field name -> JSON key

    def to_dict(self) -> Dict[str, Any]:
        return {
            self._ALIASES.get(f.name, f.name): _plain(getattr(self, f.name))
            for f in fields(self)  # type: ignore[arg-type]
        }

    @classmethod
    def from_dict(cls, data: Any):
        _check(isinstance(data, dict), f"{cls.__name__}: expected object, got {type(data).__name__}")
        rev = {json_key: py for py, json_key in cls._ALIASES.items()}
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        kwargs: Dict[str, Any] = {}
        for key, value in data.items():
            _check(key not in cls._ALIASES, f"{cls.__name__}: use JSON key {cls._ALIASES.get(key)!r}, not {key!r}")
            name = rev.get(key, key)
            _check(name in known, f"{cls.__name__}: unknown field {key!r}")
            kwargs[name] = value
        missing = sorted(known - kwargs.keys())
        _check(not missing, f"{cls.__name__}: missing fields {missing}")
        return cls(**kwargs)


# --------------------------------------------------------------------------
# Brief section 3.3 contracts
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Message(_Contract):
    """One chat message. For kind="voice", `text` is the transcript (pasted or
    speech-to-text) and "" if none yet; `media_ref` is the audio file name."""

    msg_id: int
    ts: str
    sender: str
    kind: str
    text: str
    media_ref: Optional[str]

    def __post_init__(self):
        _check(_is_int(self.msg_id) and self.msg_id >= 1, "Message.msg_id must be int >= 1")
        _iso_dt("Message.ts", self.ts)
        _str("Message.sender", self.sender)
        _enum("Message.kind", self.kind, MESSAGE_KINDS)
        _str("Message.text", self.text, nonempty=False)
        _check(self.media_ref is None or isinstance(self.media_ref, str), "Message.media_ref must be str|null")
        if self.kind in ("voice", "image"):
            _check(bool(self.media_ref), f"Message.kind={self.kind} requires media_ref")


@dataclass(frozen=True)
class Indicator(_Contract):
    """An extracted identifier. `span` is [start,end) inside the message text
    (for source="image": inside the OCR/QR text of that image, CR-3)."""

    id: str
    case_id: str
    msg_id: int
    type: str
    value_norm: str
    value_raw: str
    source: str
    confidence: str
    span: List[int]

    def __post_init__(self):
        _str("Indicator.id", self.id)
        _str("Indicator.case_id", self.case_id)
        _check(_is_int(self.msg_id) and self.msg_id >= 1, "Indicator.msg_id must be int >= 1")
        _enum("Indicator.type", self.type, INDICATOR_TYPES)
        _str("Indicator.value_norm", self.value_norm)
        _str("Indicator.value_raw", self.value_raw)
        _enum("Indicator.source", self.source, INDICATOR_SOURCES + PROVISIONAL_INDICATOR_SOURCES)
        _enum("Indicator.confidence", self.confidence, CONFIDENCES)
        _span("Indicator.span", self.span)


@dataclass(frozen=True)
class Cue(_Contract):
    msg_id: int
    type: str
    severity: str
    excerpt: str

    def __post_init__(self):
        _check(_is_int(self.msg_id) and self.msg_id >= 1, "Cue.msg_id must be int >= 1")
        _enum("Cue.type", self.type, CUE_TYPES)
        _enum("Cue.severity", self.severity, CUE_SEVERITIES)
        _str("Cue.excerpt", self.excerpt)


@dataclass(frozen=True)
class VoiceResult(_Contract):
    """Claude B's output per voice note. `file_id` == Message.media_ref."""

    file_id: str
    state: str
    score: Optional[float]
    threshold: Optional[float]
    speech_seconds: float
    reasons: List[str]
    model_version: str

    def __post_init__(self):
        _str("VoiceResult.file_id", self.file_id)
        _enum("VoiceResult.state", self.state, VOICE_STATES)
        _opt_num("VoiceResult.score", self.score)
        _opt_num("VoiceResult.threshold", self.threshold)
        _check(_is_num(self.speech_seconds) and self.speech_seconds >= 0, "VoiceResult.speech_seconds must be >= 0")
        _str_list("VoiceResult.reasons", self.reasons)
        _str("VoiceResult.model_version", self.model_version)
        if self.state in ("flagged", "no_signal"):
            _check(self.score is not None and self.threshold is not None,
                   f"VoiceResult state={self.state} requires score and threshold")
        else:
            _check(len(self.reasons) >= 1, "VoiceResult state=cant_assess requires at least one reason")


@dataclass(frozen=True)
class Evidence(_Contract):
    """One finding. JSON key for `class_` is "class"."""

    _ALIASES: ClassVar[Dict[str, str]] = {"class_": "class"}

    evidence_id: str
    payee_id: str
    lane: str
    class_: str
    claimed: str
    observed: str
    source: str
    as_of: str
    limitation: str

    def __post_init__(self):
        _str("Evidence.evidence_id", self.evidence_id)
        _str("Evidence.payee_id", self.payee_id)  # an Indicator.id, or "CASE" (CR-4)
        _enum("Evidence.lane", self.lane, EVIDENCE_LANES)
        _enum("Evidence.class", self.class_, EVIDENCE_CLASSES)
        _str("Evidence.claimed", self.claimed)
        _str("Evidence.observed", self.observed)
        _str("Evidence.source", self.source)
        _iso_date("Evidence.as_of", self.as_of)
        _str("Evidence.limitation", self.limitation)  # every finding must state its limit
        if self.lane in ("voice", "speaker"):
            _check(self.class_ == "E", "voice/speaker evidence must be class E (model output)")
        if self.lane == "registry":
            _check(self.class_ == "C", "registry evidence must be class C")
        if self.lane == "payee_name" and self.class_ == "A":
            _check("user-reported" in self.source.lower(),
                   "class A payee_name evidence must be labelled 'user-reported' in source (invariant 4)")


@dataclass(frozen=True)
class Decision(_Contract):
    payee_id: str
    result: str
    rule_id: str
    reasons: List[str]
    evidence_ids: List[str]
    next_step: str

    def __post_init__(self):
        _str("Decision.payee_id", self.payee_id)
        _enum("Decision.result", self.result, DECISION_RESULTS)
        _enum("Decision.rule_id", self.rule_id, RULE_IDS)
        _check(RESULT_TO_RULE[self.result] == self.rule_id,
               f"Decision.rule_id {self.rule_id!r} does not match result {self.result!r}")
        _str_list("Decision.reasons", self.reasons)
        _check(len(self.reasons) >= 1, "Decision.reasons must not be empty")
        _str_list("Decision.evidence_ids", self.evidence_ids)
        if self.result in ("LINKED", "NAME_DISCREPANCY", "REGISTRATION_CONFLICT", "NO_MAJOR_ISSUE"):
            _check(len(self.evidence_ids) >= 1, f"{self.result} must cite at least one evidence_id")
        _str("Decision.next_step", self.next_step)
        if self.result == "NO_MAJOR_ISSUE":
            _check(NOT_A_GUARANTEE in self.next_step,
                   f"NO_MAJOR_ISSUE next_step must contain {NOT_A_GUARANTEE!r} (invariant 5)")


# --------------------------------------------------------------------------
# Brief section 19 contracts (audio + image only)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MediaComponent(_Contract):
    name: str
    state: str
    score: Optional[float]

    def __post_init__(self):
        _str("MediaComponent.name", self.name)
        _str("MediaComponent.state", self.state)
        _opt_num("MediaComponent.score", self.score)


@dataclass(frozen=True)
class MediaResult(_Contract):
    file_id: str
    modality: str
    state: str
    score: Optional[float]
    threshold: Optional[float]
    components: List[MediaComponent]
    reasons: List[str]
    model_version: str

    def __post_init__(self):
        _str("MediaResult.file_id", self.file_id)
        _enum("MediaResult.modality", self.modality, MODALITIES)
        _enum("MediaResult.state", self.state, VOICE_STATES)
        _opt_num("MediaResult.score", self.score)
        _opt_num("MediaResult.threshold", self.threshold)
        _check(isinstance(self.components, list) and all(isinstance(c, MediaComponent) for c in self.components),
               "MediaResult.components must be list[MediaComponent]")
        _str_list("MediaResult.reasons", self.reasons)
        _str("MediaResult.model_version", self.model_version)

    @classmethod
    def from_dict(cls, data: Any):
        _check(isinstance(data, dict), "MediaResult: expected object")
        data = dict(data)
        comps = data.get("components")
        _check(isinstance(comps, list), "MediaResult.components must be a list")
        data["components"] = [MediaComponent.from_dict(c) for c in comps]
        return super().from_dict(data)


@dataclass(frozen=True)
class FrameFinding(_Contract):
    """For still images use t_sec=0.0. `type` is "qr" or "ocr_text". No video frames."""

    file_id: str
    t_sec: float
    type: str
    value_raw: str
    indicator_ids: List[str]

    def __post_init__(self):
        _str("FrameFinding.file_id", self.file_id)
        _check(_is_num(self.t_sec) and self.t_sec >= 0, "FrameFinding.t_sec must be >= 0")
        _enum("FrameFinding.type", self.type, ("qr", "ocr_text"))
        _str("FrameFinding.value_raw", self.value_raw)
        _str_list("FrameFinding.indicator_ids", self.indicator_ids)


# --------------------------------------------------------------------------
# PROVISIONAL: not in the brief's contract. See CHANGES_REQUESTED.md CR-5..CR-7.
# Added only so the fixtures are complete; B and C should treat as unstable.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AmountMention(_Contract):
    """A rupee amount tied to a payee (CR-5). Needed for the 1930/NCRP filing sheet."""

    msg_id: int
    payee_id: str
    value_inr: int
    raw: str
    span: List[int]

    def __post_init__(self):
        _check(_is_int(self.msg_id) and self.msg_id >= 1, "AmountMention.msg_id must be int >= 1")
        _str("AmountMention.payee_id", self.payee_id)
        _check(_is_int(self.value_inr) and self.value_inr > 0, "AmountMention.value_inr must be int > 0")
        _str("AmountMention.raw", self.raw)
        _span("AmountMention.span", self.span)


@dataclass(frozen=True)
class UserCheck(_Contract):
    """What the user typed from their own bank/UPI app (CR-6). Becomes class A evidence."""

    payee_id: str
    observed_name: str
    source: str
    as_of: str

    def __post_init__(self):
        _str("UserCheck.payee_id", self.payee_id)
        _str("UserCheck.observed_name", self.observed_name)
        _str("UserCheck.source", self.source)
        _check("user-reported" in self.source.lower(), "UserCheck.source must say 'user-reported'")
        _iso_date("UserCheck.as_of", self.as_of)


@dataclass(frozen=True)
class CaseContext(_Contract):
    """Inputs about the case itself (CR-6): confirmed firm + the money-already-sent toggle."""

    case_id: str
    claimed_firm: str
    money_already_sent: bool
    as_of: str

    def __post_init__(self):
        _str("CaseContext.case_id", self.case_id)
        _str("CaseContext.claimed_firm", self.claimed_firm)
        _check(isinstance(self.money_already_sent, bool), "CaseContext.money_already_sent must be bool")
        _iso_date("CaseContext.as_of", self.as_of)


@dataclass(frozen=True)
class CaseResult(_Contract):
    """Worst per-payee decision (CR-7). Ties go to the payee that appears first in the chat."""

    case_id: str
    result: str
    rule_id: str
    deciding_payee_id: str
    next_step: str
    money_already_sent: bool

    def __post_init__(self):
        _str("CaseResult.case_id", self.case_id)
        _enum("CaseResult.result", self.result, DECISION_RESULTS)
        _enum("CaseResult.rule_id", self.rule_id, RULE_IDS)
        _check(RESULT_TO_RULE[self.result] == self.rule_id, "CaseResult.rule_id does not match result")
        _str("CaseResult.deciding_payee_id", self.deciding_payee_id)
        _str("CaseResult.next_step", self.next_step)
        _check(isinstance(self.money_already_sent, bool), "CaseResult.money_already_sent must be bool")
        if self.result == "NO_MAJOR_ISSUE":
            _check(NOT_A_GUARANTEE in self.next_step, "NO_MAJOR_ISSUE next_step must contain the guarantee disclaimer")
