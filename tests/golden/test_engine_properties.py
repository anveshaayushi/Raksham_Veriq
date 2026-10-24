"""FINALE: truth-table and property tests for the decision ladder and the name matcher.

Properties (brief section 6, deck p6 and p9):
- more risk never gives a milder answer (adding a hard cue, a voice flag, a registry link, a registration conflict)
- a voice result never clears a payee; no_signal never upgrades INCONCLUSIVE to NO_MAJOR_ISSUE
- registry "unavailable" is never treated as "clean"
- NO_MAJOR_ISSUE always carries "This is not a guarantee." and needs a class A name match
- gateway handles, personal-looking names, initials and near spellings are "unverified", never a discrepancy
"""
import itertools

import pytest

from core.schemas import NOT_A_GUARANTEE, RESULT_RANK, Cue, Evidence, Indicator
from match import match_names
from registry.interface import RegistryResult
from rules import decide

FIRM = "Navyug Broking Pvt Ltd"
P = Indicator(id="t-I1", case_id="t", msg_id=1, type="upi_vpa", value_norm="x.y@upi", value_raw="x.y@upi",
              source="text", confidence="high", span=[0, 7])


def ev(eid, lane, cls, observed, payee="t-I1"):
    return Evidence(evidence_id=eid, payee_id=payee, lane=lane, class_=cls, claimed="c", observed=observed,
                    source="user-reported: test" if lane == "payee_name" else "test", as_of="2026-10-24", limitation="l")


NAME = {"none": None, "match": "NAVYUG BROKING PRIVATE LIMITED", "disc": "SHREE GANESH TRADERS",
        "unver": "RAMESH KUMAR"}
REG = {"none": None, "listed": "Listed as 'Navyug Broking Private Limited' in the snapshot",
       "missing": "INZ000DEMO99 not present in the snapshot"}
VOICE = {"none": None, "no_signal": "no_signal (stub value, not a measurement)", "cant": "cant_assess: too short",
         "flagged": "flagged (stub value, not a measurement)"}
REGISTRY = {"none": None, "clean": "clean", "linked": "linked", "unavailable": "unavailable"}


def run(name="none", reg="none", voice="none", registry="none", hard=False):
    evidence, regs = [], []
    if NAME[name]:
        evidence.append(ev("t-E1", "payee_name", "A", NAME[name]))
    if REG[reg]:
        evidence.append(ev("t-E2", "registration", "B", REG[reg], payee="CASE"))
    if VOICE[voice]:
        evidence.append(ev("t-E3", "voice", "E", VOICE[voice], payee="CASE"))
    if REGISTRY[registry]:
        regs.append(RegistryResult("t-I1", REGISTRY[registry], 2 if registry == "linked" else 0, False, "test"))
        evidence.append(ev("t-E4", "registry", "C", {"clean": "no matching report", "linked": "linked: 2 reporters",
                                                     "unavailable": "registry unavailable: x"}[registry]))
    cues = [Cue(msg_id=1, type="fee_to_withdraw", severity="hard", excerpt="tax to withdraw")] if hard else []
    sebi = [Indicator(id="t-I2", case_id="t", msg_id=1, type="sebi_reg", value_norm="INZ000DEMO99",
                      value_raw="INZ000DEMO99", source="text", confidence="high", span=[0, 12])] if reg != "none" else []
    (d,) = decide(claimed_firm=FIRM, payees=[P], indicators=[P] + sebi, cues=cues, evidence=evidence, voice=[],
                  registry=regs)
    return d


GRID = list(itertools.product(NAME, REG, VOICE, REGISTRY, [False, True]))


@pytest.mark.parametrize("name,reg,voice,registry,hard", GRID)
def test_every_combination_is_valid_and_honest(name, reg, voice, registry, hard):
    d = run(name, reg, voice, registry, hard)
    assert d.rule_id and d.reasons  # Decision validates itself against the contract
    if d.result == "NO_MAJOR_ISSUE":
        assert name == "match" and not hard and voice in ("none", "no_signal") and reg != "missing"
        assert registry != "linked" and NOT_A_GUARANTEE in d.next_step
    if registry == "linked":
        assert d.result == "LINKED"
    if name == "unver":
        assert d.result != "NAME_DISCREPANCY"


@pytest.mark.parametrize("name,reg,voice,registry,hard", GRID)
def test_more_risk_never_milder(name, reg, voice, registry, hard):
    base = RESULT_RANK[run(name, reg, voice, registry, hard).result]
    riskier = [run(name, reg, voice, registry, True), run(name, reg, "flagged", registry, hard),
               run(name, reg, voice, "linked", hard)]
    if reg != "none":
        riskier.append(run(name, "missing", voice, registry, hard))
    assert all(RESULT_RANK[r.result] <= base for r in riskier)


@pytest.mark.parametrize("voice", ["no_signal", "cant", "flagged"])
def test_voice_never_clears(voice):
    assert run("none", voice=voice).result != "NO_MAJOR_ISSUE"
    assert RESULT_RANK[run("match", voice=voice).result] <= RESULT_RANK[run("match").result]


def test_unavailable_registry_is_not_clean():
    d = run("match", registry="unavailable")
    assert "t-E4" not in d.evidence_ids


@pytest.mark.parametrize("claimed,observed,verdict", [
    ("Navyug Wealth Research Pvt Ltd", "SHREE GANESH TRADERS", "discrepancy"),
    ("Navyug Broking Pvt Ltd", "NAVYUG BROKING PRIVATE LIMITED", "match"),
    ("HDFC Securities Ltd", "HDFC SEC LTD", "match"),
    ("Navyug Broking", "Razorpay Software Pvt Ltd", "unverified"),
    ("Navyug Broking", "RAMESH KUMAR", "unverified"),
    ("Navyug Wealth Research", "NWR PVT LTD", "unverified"),
    ("Navyug Broking", "NAVYOG BROKING", "unverified"),
    ("Navyug Wealth Research", "WEALTH RESEARCH SERVICES", "unverified"),
    ("TradeMax Pro", "", "unverified"),
])
def test_name_matcher_classes(claimed, observed, verdict):
    assert match_names(claimed, observed)[0] == verdict
