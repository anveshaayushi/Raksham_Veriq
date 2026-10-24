"""Payee-name matcher: does the name the user's bank/UPI app showed belong to the claimed firm?

FINALE, 24 Oct 2026. Claude A's token matcher, ported and extended by Claude C at the team's request (CR-C13).

match_names(claimed, observed) -> (verdict, reason)
    verdict "match"        : shares a distinctive word with the claimed firm
    verdict "discrepancy"  : a business name with no distinctive word in common  -> can decide NAME_DISCREPANCY
    verdict "unverified"   : we can't tell, so we don't accuse (deck p9: false-positive classes)
        - payment gateway / aggregator names (Razorpay, Cashfree, ...): the merchant's name is not shown
        - a personal-looking name (could be the firm's proprietor or a mule; we can't tell which)
        - an abbreviation or initials of the claimed firm ("NWR PVT LTD")
        - a near spelling / transliteration variant ("Navyog" vs "Navyug")
        - nothing distinctive left on one side
Generic words (Pvt, Ltd, Traders, Wealth, Securities, ...) never count as a shared word on their own.
"""

from __future__ import annotations

import re
import unicodedata

GENERIC = {
    # legal forms
    "pvt", "private", "ltd", "limited", "llp", "inc", "corp", "corporation", "co", "company", "plc", "opc",
    # finance words that many unrelated firms share
    "wealth", "research", "securities", "security", "broking", "brokers", "broker", "advisory", "advisors", "advisers",
    "investment", "investments", "capital", "finance", "financial", "finserv", "fintech", "markets", "market", "trading",
    "trade", "trades", "stock", "stocks", "shares", "equity", "money", "fund", "funds", "asset", "assets", "management",
    "consultancy", "consultants", "services", "service", "solutions", "global", "india", "indian", "international",
    # shop / trading-style words
    "traders", "trader", "enterprises", "enterprise", "agency", "agencies", "store", "stores", "industries", "group",
    "associates", "ventures", "mart", "the", "and", "of", "pro",
}
BUSINESS_MARKERS = GENERIC - {"the", "and", "of", "india", "indian", "global", "international", "pro"}
GATEWAYS = ("razorpay", "cashfree", "payu", "billdesk", "ccavenue", "juspay", "easebuzz", "instamojo", "phonepe",
            "paytm payments", "bharatpe", "pine labs", "mswipe", "setu")
HONORIFICS = {"mr", "mrs", "ms", "shri", "smt", "sri", "kumari", "dr"}


def _tokens(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bpvt\.?\s*ltd\.?\b", " pvt ltd ", s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def _distinctive(tokens: list[str]) -> set[str]:
    return {t for t in tokens if t not in GENERIC and t not in HONORIFICS and len(t) > 1}


def _near(a: str, b: str) -> bool:
    """One edit apart (insert/delete/substitute) for words of 5+ letters: likely the same word, spelled differently."""
    if min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def match_names(claimed: str, observed: str) -> tuple[str, str]:
    c_tok, o_tok = _tokens(claimed or ""), _tokens(observed or "")
    if not c_tok or not o_tok:
        return "unverified", "a name is missing"
    o_low = " ".join(o_tok)
    for g in GATEWAYS:
        if g in o_low:
            return "unverified", f"payment gateway or aggregator ({g}): the app does not show the merchant behind it"
    c_d, o_d = _distinctive(c_tok), _distinctive(o_tok)
    if not c_d:
        return "unverified", "the claimed firm's name has no distinctive word to compare"
    shared = c_d & o_d
    if shared:
        return "match", f"shares the distinctive word(s) {', '.join(sorted(shared))}"
    if any(_near(a, b) for a in c_d for b in o_d):
        return "unverified", "a near spelling of the claimed name (could be a variant or a look-alike)"
    initials = "".join(t[0] for t in c_tok if t not in {"pvt", "private", "ltd", "limited", "and", "of", "the"})
    if any(len(t) >= 2 and initials.startswith(t) for t in o_tok if t not in GENERIC):
        return "unverified", "looks like initials of the claimed firm"
    if not o_d:
        return "unverified", "the shown name has only generic words"
    is_business = any(t in BUSINESS_MARKERS for t in o_tok)
    if not is_business and 1 <= len([t for t in o_tok if t not in HONORIFICS]) <= 4:
        return "unverified", "a personal-looking name: could be the firm's proprietor or someone else; we can't tell"
    return "discrepancy", f"no distinctive word in common with '{claimed.strip()}'"
