"""Regression tests for the fixes made AFTER the pre-registered run of 25 Oct 2026 (results/prereg/).

Examples here are written fresh (new names and IDs), not copied from the datasets, so these tests check the general
rule, not the benchmark cases. Each block names the failure class it guards.
"""
from __future__ import annotations

import pytest

from extract import RX, _obfuscated_vpas, normalise, vpa_from
from match import match_names


def vpas(text):
    return [vpa_from(r) for r, _, _ in _obfuscated_vpas(normalise(text))]


@pytest.mark.parametrize("text, want", [
    ("pay to meena dot k at okicici today", "meena.k@okicici"),
    ("UPI: arjun.v(at)ybl", "arjun.v@ybl"),
    ("id: om-traders[at]paytm", "om-traders@paytm"),
    ("send on rohan underscore p at the rate oksbi", "rohan_p@oksbi"),
    ("number pe bhejo: 98765 43210 @ ybl", "9876543210@ybl"),
    ("search s h a dot pay dot 9 @ ibl in the app", "sha.pay.9@ibl"),
    ("use lata_m22 at okaxis", "lata_m22@okaxis"),
    ("new id: devika dash r at quillbank", "devika-r@quillbank"),
])
def test_obfuscated_upi_ids_are_read(text, want):
    assert vpas(text) == [want]


@pytest.mark.parametrize("text", ["meet me at office at 5", "I am at home", "pay at the counter", "Ravi at Navyug",
                                  "reach us at support desk", "we met at noon"])
def test_plain_at_in_a_sentence_is_not_a_upi_id(text):
    assert vpas(text) == []


@pytest.mark.parametrize("text, digits", [
    ("Account: 1100 2233 4455 6", "1100223344556"),
    ("A/c 2200-3311-4422-5", "2200331144225"),
    ("acc no. 330044 5566 7788", "33004455667788"),
    ("account number 556677889900", "556677889900"),
])
def test_grouped_account_numbers(text, digits):
    got = [m.group(1) for m in RX["bank_account"].finditer(normalise(text))]
    assert len(got) == 1 and "".join(ch for ch in got[0] if ch.isdigit()) == digits


def test_account_number_does_not_swallow_a_following_amount():
    got = [m.group(1) for m in RX["bank_account"].finditer("a/c 123456789012 15000 rupees")]
    assert got == ["123456789012"]


def test_spaced_phone_found_but_not_the_digits_of_a_upi_id():
    assert [m.group(1) for m in RX["phone"].finditer("call 98123 45678 now")] == ["98123 45678"]
    assert [m.group(1) for m in RX["phone"].finditer("UPI - 9812345678@ybl")] == []


def test_extracted_payees_are_normalised():
    from app.adapters.extract import payees, run
    ex = run("20/10/2026, 8:59 pm - Agent: pay to meena dot k at okicici\n"
             "20/10/2026, 9:00 pm - Agent: or A/c 2200-3311-4422-5\n", "t")
    assert [p.value_norm for p in payees(ex.indicators)] == ["meena.k@okicici", "2200331144225"]


@pytest.mark.parametrize("claimed, shown, want", [
    # purpose words on the firm's own collection or billing account: same firm
    ("Corvid Mutual Fund", "CORVID MUTUAL FUND COLLECTIONS", "match"),
    ("Brightline Power", "BRIGHTLINE POWER BILL PAYMENTS", "match"),
    ("Palmera Life", "PALMERA LIFE INSURANCE LTD", "match"),
    # ...but a purpose word that REPLACES the firm's business type is a look-alike
    ("Corvid Wealth Research Pvt Ltd", "CORVID PAYMENTS", "lookalike"),
    # transliteration variants, joined/split words, initials with dots, city/branch suffix, abbreviations
    ("Shri Durga Provision Store", "SREE DURGA PROVISION STORE", "match"),
    # a differently spelled word is never a match (transliteration or copycat: can't tell), never an accusation
    ("Lakshmi Ganesh Textiles", "LAXMI GANESH TEXTILES", "unverified"),
    ("Cobaltine Meadow Capital", "COBALTENE MEADOW CAPITAL", "unverified"),
    ("Jai Ambe Traders", "JAIAMBE TRADERS", "match"),
    ("Ramkrishna Electricals", "RAM KRISHNA ELECTRICALS", "match"),
    ("P. K. Verma & Sons", "PK VERMA AND SONS", "match"),
    ("Corvid Advisors Pvt Ltd", "CORVID ADVISORS PVT LTD NAGPUR BRANCH", "match"),
    ("Bharat Steel Brothers", "BHARAT STEEL BROS", "match"),
    # a number appended to the firm's name: possibly another account in a similar name
    ("Corvid Research", "CORVID RESEARCH 7", "lookalike"),
    # can't tell: short forms, initials, aggregators
    ("Corvidale Capital Pvt Ltd", "CORVI CAP", "unverified"),
    ("Corvid Wealth Pvt Ltd", "CWPL", "unverified"),
    ("Corvid Wealth Pvt Ltd", "SWIFTPAYZ MERCHANT SERVICES", "unverified"),
    # still a discrepancy: an unrelated shop, even with a personal name in it
    ("Corvid Wealth Pvt Ltd", "MANOJ PAN SHOP", "discrepancy"),
    ("Corvid Wealth Pvt Ltd", "ROYAL FASHION COLLECTION", "discrepancy"),
    # still a near-spelling look-alike is never a match
    ("Corvid Wealth Research", "CORVYD WEALTH RESEARCH", "unverified"),
])
def test_name_matcher_after_prereg(claimed, shown, want):
    assert match_names(claimed, shown)[0] == want, match_names(claimed, shown)


def test_link_only_payment_gets_a_check_before_you_pay_answer():
    from app.case import build_case
    c = build_case(case_id="lnk", chat_text="20/10/2026, 8:59 pm - Desk: Pay the ₹99 fee here: https://pay.example.test/x/1\n",
                   claimed_firm="Example Desk", checks={})
    assert c.case_result() is None and c.payment_links() == ["https://pay.example.test/x/1"]
    c2 = build_case(case_id="lnk2", chat_text="20/10/2026, 8:59 pm - Gil: read the basics at https://blog.example.test/sip\n",
                    claimed_firm="Example", checks={})
    assert c2.payment_links() == []


def test_kit_does_not_score_its_own_readme_as_a_chat(tmp_path):
    import csv
    from eval.cli import main
    kit = tmp_path / "kit"
    (kit / "scam").mkdir(parents=True)
    (kit / "README.txt").write_text("notes for the kit", encoding="utf-8")
    (kit / "scam" / "a.txt").write_text("20/10/2026, 8:59 pm - A: pay 500 to x.y@ybl\n", encoding="utf-8")
    out = tmp_path / "p.csv"
    main(["--input", str(kit), "--out", str(out), "--detector", "none"])
    rows = {r["file_id"]: r for r in csv.DictReader(open(out, encoding="utf-8"))}
    assert rows["README.txt"]["modality"] == "other" and rows["scam/a.txt"]["modality"] == "chat"
