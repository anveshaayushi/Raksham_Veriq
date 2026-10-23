import dataclasses

from app.contracts import Decision, case_result
from app.next_steps import MONEY_SENT_STEP, NOT_A_GUARANTEE, display_next_step, with_money_sent
from app.text_safety import md_escape, redact

D = Decision(payee_id="p1", result="NAME_DISCREPANCY", rule_id="NAME_DISC", reasons=["x"], evidence_ids=["e1"], next_step="Don't pay.")


def test_money_sent_changes_only_next_step():
    d2 = with_money_sent(D, True)
    assert d2.next_step == MONEY_SENT_STEP
    for f in dataclasses.fields(D):
        if f.name != "next_step":
            assert getattr(d2, f.name) == getattr(D, f.name)
    assert with_money_sent(D, False) is D
    assert with_money_sent({"result": "INCONCLUSIVE", "next_step": "a"}, True) == {"result": "INCONCLUSIVE", "next_step": MONEY_SENT_STEP}
    assert NOT_A_GUARANTEE in with_money_sent({"result": "NO_MAJOR_ISSUE", "next_step": "a"}, True)["next_step"]


def test_no_major_issue_always_says_not_a_guarantee():
    d = {"result": "NO_MAJOR_ISSUE", "next_step": "All good."}  # an engine that forgot the line
    assert NOT_A_GUARANTEE in display_next_step(d)
    assert NOT_A_GUARANTEE in display_next_step(with_money_sent(d, True))
    assert NOT_A_GUARANTEE not in display_next_step(D)


def test_case_result_is_worst_payee():
    a = {"result": "NO_MAJOR_ISSUE"}
    b = {"result": "HUMAN_REVIEW"}
    assert case_result([a, b]) == "HUMAN_REVIEW" and case_result([]) is None


def test_markdown_escaping_neutralises_links_and_html():
    s = md_escape("[click](http://evil) <script>alert(1)</script> **bold** ![img](x)")
    for raw in ("[click](", "<script>", "**bold**", "![img]"):
        assert raw not in s


def test_redact():
    t = redact("A/c 50210012345021 call 9876543210")
    assert "50210012345021" not in t and "XX5021" in t and "9876543210" not in t and "3210" in t


def test_urls_are_defanged_so_markdown_cannot_autolink():
    s = md_escape("visit http://evil.example or https://x.in or www.bad.in now")
    assert "http://" not in s and "https://" not in s and "www." not in s and "hxxp" in s
