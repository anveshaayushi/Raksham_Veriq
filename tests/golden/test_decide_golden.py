"""FINALE: the decision engine on the golden fixtures, in the fixtures' own format (replaces Claude A's first draft,
which used types core/schemas.py does not define; CR-C13). Result, rule_id and the SET of evidence_ids must match."""
import dataclasses
import json
from pathlib import Path

import pytest

from core.schemas import NOT_A_GUARANTEE, Cue, Evidence, Indicator, VoiceResult
from extract import amounts, extract, payees
from parsing import parse_chat
from registry.interface import RegistryResult
from rules import case_evidence, case_result, decide

FX = sorted((Path(__file__).resolve().parents[2] / "fixtures").glob("scenario_*.json"))


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def registry_of(d, pays):
    return [RegistryResult(p.id, d["registry_stub"].get(p.id, "unavailable"), 0, False, "registry STUB (fixture)")
            for p in pays]


@pytest.mark.parametrize("path", FX, ids=lambda p: p.stem)
def test_decide_on_fixture_evidence_matches_exactly(path):
    d = load(path)
    e = d["expected"]
    inds = [Indicator.from_dict(x) for x in e["indicators"]]
    pays = payees(inds)
    got = decide(claimed_firm=d["case"]["claimed_firm"], payees=pays, indicators=inds,
                 cues=[Cue.from_dict(x) for x in e["cues"]], evidence=[Evidence.from_dict(x) for x in e["evidence"]],
                 voice=[VoiceResult.from_dict(x) for x in e["voice_results"]], registry=registry_of(d, pays))
    want = {x["payee_id"]: x for x in e["decisions"]}
    assert [g.payee_id for g in got] == [x["payee_id"] for x in e["decisions"]]
    for g in got:
        w = want[g.payee_id]
        assert (g.result, g.rule_id, set(g.evidence_ids)) == (w["result"], w["rule_id"], set(w["evidence_ids"]))
        if g.result == "NO_MAJOR_ISSUE":
            assert NOT_A_GUARANTEE in g.next_step
    assert case_result(got).result == e["case_result"]["result"]
    assert case_result(got).payee_id == e["case_result"]["deciding_payee_id"]


@pytest.mark.parametrize("path", FX, ids=lambda p: p.stem)
def test_raw_chat_end_to_end(path):
    """Raw chat text -> parse -> transcripts merged -> extract -> evidence -> decide, with no expected values used."""
    d = load(path)
    e, cid, firm = d["expected"], d["case"]["case_id"], d["case"]["claimed_firm"]
    tr = d["input"].get("transcripts") or {}
    msgs = [dataclasses.replace(m, text=tr[m.media_ref]) if m.kind == "voice" and tr.get(m.media_ref) else m
            for m in parse_chat(d["input"]["chat_txt"])]
    assert [m.to_dict() for m in msgs] == e["messages"]
    inds, cues = extract(msgs, cid)
    assert [i.to_dict() for i in inds] == e["indicators"]
    assert sorted((c.msg_id, c.type, c.severity) for c in cues) == sorted((c["msg_id"], c["type"], c["severity"])
                                                                          for c in e["cues"])
    assert [a.to_dict() for a in amounts(msgs, inds)] == e["amounts"]
    pays = payees(inds)
    name_ev = [Evidence(evidence_id=f"{cid}-E{n}", payee_id=u["payee_id"], lane="payee_name", class_="A",
                        claimed=f"payee belongs to {firm}", observed=u["observed_name"], source=u["source"],
                        as_of=u["as_of"], limitation="user-typed name")
               for n, u in enumerate(d["user_checks"], start=1)]
    voice = [VoiceResult.from_dict(x) for x in e["voice_results"]]
    reg = registry_of(d, pays)
    ev = case_evidence(case_id=cid, claimed_firm=firm, messages=msgs, indicators=inds, payees=pays,
                       payee_name_evidence=name_ev, voice=voice, registry=reg, as_of=d["case"]["as_of"])
    got = decide(claimed_firm=firm, payees=pays, indicators=inds, cues=cues, evidence=ev, voice=voice, registry=reg)
    want = {x["payee_id"]: x for x in e["decisions"]}
    gold_ev = {x["evidence_id"]: x for x in e["evidence"]}
    by_id = {x.evidence_id: x for x in ev}
    for g in got:
        w = want[g.payee_id]
        assert (g.result, g.rule_id) == (w["result"], w["rule_id"])
        assert sorted((by_id[i].lane, by_id[i].class_) for i in g.evidence_ids) == \
            sorted((gold_ev[i]["lane"], gold_ev[i]["class"]) for i in w["evidence_ids"])
    for x in ev:
        if x.lane == "voice":
            assert not any(ch.isdigit() for ch in x.observed.split("(")[-1]) or "calibrated" in x.observed  # CR-C9
