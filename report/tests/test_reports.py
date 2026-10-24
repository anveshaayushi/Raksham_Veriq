from app.case import UserCheck, build_case, demo_inputs, load_demo, report_data
from report.build import BLANK, NOT_A_GUARANTEE, STANDING_LINE, filing_sheet_html, filing_sheet_md, summary_html, summary_md


def data(sid="A", money=False, user=None, per=None, chat=None):
    fx = load_demo(sid)
    di = demo_inputs(fx)
    checks = {k: UserCheck(v["name"], v["source"], v["date"]) for k, v in di["checks"].items()}
    c = build_case(case_id=di["case_id"], chat_text=chat or di["chat_text"], claimed_firm=di["claimed_firm"], checks=checks,
                   transcripts=di["transcripts"], fixture=fx, files=[{"name": "chat.txt", "kind": "chat", "sha256": "ab" * 32}])
    return report_data(c, money_sent=money, user=user, per_payee=per)


def test_filing_sheet_fields_and_blanks():
    for out in (filing_sheet_md(data()), filing_sheet_html(data())):
        for f in ("Complainant mobile number", "Bank, wallet or merchant debited", "Account or UPI ID debited", "transaction ID (UTR)",
                  "Transaction date", "Amount paid", "Supporting screenshots", "What to say on the 1930 call", "ab" * 32):
            assert f in out, f
        plain = out.replace("\\", "")
        assert plain.count(BLANK) >= 6  # 4 personal fields + UTR/date/amount per payee
        assert STANDING_LINE in plain
        assert "30112233445021" in out  # local filing sheet keeps full identifiers
        assert "not an official complaint" in out


def test_user_entered_values_marked_and_blanks_not_invented():
    d = data(user={"mobile": "9000000001"}, per={})
    md = filing_sheet_md(d)
    assert "entered by you" in md and "UTR" in md
    assert md.count("BLANK") >= 3 and "9000000001 (entered by you)" in md  # bank, account, screenshots, UTRs, dates remain blank


def test_summary_redacts_accounts_and_phones_and_keeps_standing_line():
    d = data(user={"mobile": "9876543210", "account": "123456789012"})
    for out in (summary_md(d), summary_html(d)):
        assert "30112233445021" not in out and "5021" in out
        assert "9876543210" not in out and "123456789012" not in out
        assert "files no complaints" in out


def test_no_major_issue_disclaimer_in_reports():
    d = data("B")
    for out in (summary_md(d), summary_html(d), filing_sheet_md(d), filing_sheet_html(d)):
        assert NOT_A_GUARANTEE.rstrip(".") in out.replace("\\.", ".")


def test_untrusted_chat_text_is_escaped():
    fx = load_demo("C")
    evil = demo_inputs(fx)["chat_text"] + "09/10/26, 20:19 - TradeMax Support: <script>alert(1)</script> [win](http://evil.example)\n"
    d = data("C", chat=evil)
    h = summary_html(d) + filing_sheet_html(d)
    assert "<script>" not in h and "&lt;script&gt;" in h
    m = summary_md(d) + filing_sheet_md(d)
    assert "<script>" not in m and "[win](" not in m and "http://evil" not in m


def test_computed_results_have_no_stub_notice_but_stub_bundles_do(monkeypatch):
    assert "not a real rules-engine decision" not in summary_md(data())
    import app.case as case_mod
    monkeypatch.setattr(case_mod, "engine_available", lambda: False)
    import rules
    monkeypatch.delattr(rules, "decide")  # engine code missing -> labelled stub decisions
    assert "not a real rules-engine decision" in summary_md(data())


def test_links_are_defanged_in_markdown_reports():
    """Added in Q1 after the mutation check (M10) showed the test above never put a link into the report: the evil
    line there has no payee or cue, so it is not quoted. This one quotes a payee message that carries a link."""
    from report.build import md

    def plain(t):  # remove Markdown escape backslashes to see what a reader would see
        return t.replace("\\", "")

    assert plain(md("pay at https://evil.example/kyc or www.evil.in")) == "pay at hxxps://evil.example/kyc or www[.]evil.in"
    assert "http" not in plain(md("HTTP://evil.example")).lower().replace("hxxp", "")
    fx = load_demo("C")
    chat = demo_inputs(fx)["chat_text"] + ("09/10/26, 20:21 - TradeMax Support: Pay ₹5,000 to linkpay@upi "
                                           "or at https://evil.example/pay today\n")
    m = plain(summary_md(data("C", chat=chat)) + filing_sheet_md(data("C", chat=chat)))
    assert "linkpay@upi" in m and "https://evil" not in m and "hxxps://evil" in m
