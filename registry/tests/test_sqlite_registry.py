import sqlite3

import pytest

from registry.seed import seed
from registry.sqlite_registry import (BURST_WINDOW_S, RATE_PER_DAY, SQLiteRegistry, create_db, from_env, load_secret,
                                      new_reporter_token)

SECRET = b"test-secret-0123456789"
DAY = 86400


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def adv(self, s):
        self.t += s


@pytest.fixture
def reg(tmp_path):
    p = tmp_path / "r.db"
    create_db(p)
    c = Clock()
    return SQLiteRegistry(p, secret=SECRET, clock=c), c


def status(r, v="victim.pay@upi", t="upi_vpa"):
    return r.lookup("p1", t, v)


def test_two_independent_reporters_link(reg):
    r, c = reg
    assert r.report("upi_vpa", "victim.pay@upi", new_reporter_token()).status == "recorded"
    assert status(r).status == "clean" and "not enough to link" in status(r).note
    c.adv(BURST_WINDOW_S + 1)
    r.report("upi_vpa", "victim.pay@upi", new_reporter_token())
    res = status(r)
    assert res.status == "linked" and res.independent_reporters == 2 and not res.reviewer_confirmed


def test_one_reporter_twice_does_not_link(reg):
    r, c = reg
    tok = new_reporter_token()
    assert r.report("upi_vpa", "victim.pay@upi", tok).status == "recorded"
    c.adv(DAY)
    assert r.report("upi_vpa", "victim.pay@upi", tok).status == "duplicate"
    assert status(r).status == "clean"


def test_reviewer_confirm_links_and_reject_blocks(reg):
    r, c = reg
    r.report("upi_vpa", "a@upi", new_reporter_token())
    r.review("upi_vpa", "a@upi", "confirmed", "reviewer-1")
    res = status(r, "a@upi")
    assert res.status == "linked" and res.reviewer_confirmed
    for _ in range(3):
        c.adv(BURST_WINDOW_S + 1)
        r.report("upi_vpa", "b@upi", new_reporter_token())
    assert status(r, "b@upi").status == "linked"
    r.review("upi_vpa", "b@upi", "rejected", "reviewer-1")
    assert status(r, "b@upi").status == "clean" and "rejected" in status(r, "b@upi").note


def test_poisoning_one_token_twenty_false_reports(reg):
    r, c = reg
    tok = new_reporter_token()
    outs = []
    for i in range(20):
        outs.append(r.report("upi_vpa", f"legit.firm{i % 2}@hdfcbank", tok).status)
        c.adv(5)
    assert outs.count("recorded") <= 2 and "rate_limited" in outs
    assert status(r, "legit.firm0@hdfcbank").status == "clean" and status(r, "legit.firm1@hdfcbank").status == "clean"


def test_poisoning_five_tokens_in_one_minute(reg):
    r, c = reg
    for _ in range(5):
        assert r.report("upi_vpa", "legit.firm@hdfcbank", new_reporter_token()).status == "recorded"
        c.adv(12)
    res = status(r, "legit.firm@hdfcbank")
    assert res.status == "clean" and res.independent_reporters == 1 and "count once" in res.note


def test_daily_rate_limit(reg):
    r, c = reg
    tok = new_reporter_token()
    outs = []
    for i in range(RATE_PER_DAY + 3):
        outs.append(r.report("upi_vpa", f"p{i}@upi", tok).status)
        c.adv(61)
    assert outs[:RATE_PER_DAY] == ["recorded"] * RATE_PER_DAY and set(outs[RATE_PER_DAY:]) == {"rate_limited"}


def test_gateway_handles_never_stored_or_linked(reg):
    r, c = reg
    for _ in range(4):
        assert r.report("upi_vpa", "shop@razorpay", new_reporter_token()).status == "excluded"
        c.adv(BURST_WINDOW_S + 1)
    assert r.review("upi_vpa", "shop@razorpay", "confirmed", "x").status == "excluded"
    assert status(r, "shop@razorpay").status == "unavailable"


def test_old_reports_decay(reg):
    r, c = reg
    for _ in range(2):
        r.report("upi_vpa", "old@upi", new_reporter_token())
        c.adv(BURST_WINDOW_S + 1)
    assert status(r, "old@upi").status == "linked"
    c.adv(181 * DAY)
    assert status(r, "old@upi").status == "clean"


def test_unavailable_never_clean(tmp_path):
    assert SQLiteRegistry(tmp_path / "missing.db", secret=SECRET).lookup("p", "upi_vpa", "x@upi").status == "unavailable"
    assert not (tmp_path / "missing.db").exists()  # lookup must not create a database
    p = tmp_path / "r.db"
    create_db(p)
    assert SQLiteRegistry(p, secret=b"").lookup("p", "upi_vpa", "x@upi").status == "unavailable"
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"not a database at all, just bytes")
    assert SQLiteRegistry(junk, secret=SECRET).lookup("p", "upi_vpa", "x@upi").status == "unavailable"


def test_locked_database_is_unavailable(tmp_path):
    p = tmp_path / "r.db"
    create_db(p)
    lock = sqlite3.connect(p)
    lock.execute("BEGIN EXCLUSIVE")
    try:
        r = SQLiteRegistry(p, secret=SECRET)
        assert r.lookup("p", "upi_vpa", "x@upi").status == "unavailable"
        assert r.report("upi_vpa", "x@upi", new_reporter_token()).status == "unavailable"
    finally:
        lock.rollback()
        lock.close()


def test_no_raw_identifiers_or_tokens_in_the_file(reg):
    r, c = reg
    tok = new_reporter_token()
    r.report("bank_account", "30112233445021", tok)
    r.report("upi_vpa", "ramesh.k@upi", new_reporter_token())
    raw = r.db_path.read_bytes()
    for s in (b"30112233445021", b"ramesh.k@upi", tok.encode()):
        assert s not in raw


def test_secret_from_env_and_file(monkeypatch, tmp_path):
    monkeypatch.delenv("VERIQ_REGISTRY_SECRET", raising=False)
    monkeypatch.delenv("VERIQ_REGISTRY_SECRET_FILE", raising=False)
    assert load_secret() is None
    f = tmp_path / "secret.txt"
    f.write_text("file-secret-0123456789\n")
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET_FILE", str(f))
    assert load_secret() == b"file-secret-0123456789"
    monkeypatch.setenv("VERIQ_REGISTRY_SECRET", "short")
    assert load_secret() is None  # too short is refused, not padded
    monkeypatch.delenv("VERIQ_REGISTRY_DB", raising=False)
    assert from_env() is None


def test_seed_gives_linked_and_unlinked(tmp_path):
    p = tmp_path / "seed.db"
    seed(str(p), SECRET)
    r = SQLiteRegistry(p, secret=SECRET)
    assert r.lookup("p", "upi_vpa", "fixture.linked@upi").status == "linked"
    assert r.lookup("p", "upi_vpa", "sunita.t@upi").status == "linked"
    assert r.lookup("p", "bank_account", "30112233445021").status == "clean"
    assert r.lookup("p", "upi_vpa", "never.seen@upi").status == "clean"
    assert SQLiteRegistry(p, secret=b"a-different-secret-1234").lookup("p", "upi_vpa", "sunita.t@upi").status == "clean"
