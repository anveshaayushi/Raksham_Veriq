"""SQLite cross-victim registry (FINALE, Claude C, prompt C3). Same interface as registry/stub.py: lookup() -> RegistryResult.

Plain idea: "have other people, independently, reported this payee?" without storing anyone's identifiers or chats.

Technical rules (brief section 8):
- Only keyed HMAC-SHA256 pseudonyms are stored (registry.interface.hmac_indicator, namespaced by indicator type).
  Raw UPI IDs, account numbers and reporter tokens are never written to the database.
  This is pseudonymisation, not anonymity: whoever holds the secret can test a guess.
- The secret comes from the environment: VERIQ_REGISTRY_SECRET, or a file named by VERIQ_REGISTRY_SECRET_FILE.
  No secret -> the registry is "unavailable"; it never falls back to a built-in key.
- One reporter_token per user session (new_reporter_token()); stored only as a keyed hash.
- "linked" needs >= 2 INDEPENDENT reporters within DECAY_DAYS, or a reviewer confirmation. A reviewer rejection
  blocks linking. Reports from different tokens inside one BURST_WINDOW_S count as ONE independent reporter
  (defence against a burst of fresh tokens: poisoning a legitimate payee needs patience, and a reviewer can see it).
- Rate limit per reporter token: RATE_PER_MINUTE and RATE_PER_DAY.
- Non-attributable handles (payment gateways, aggregators) are never stored and never linked.
- Database missing, locked or unreadable -> status "unavailable", never "clean".
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .interface import (DECAY_DAYS, LINK_MIN_INDEPENDENT_REPORTERS, RegistryResult, hmac_indicator,
                        is_non_attributable)

SOURCE = "SQLite registry (pseudonymised; synthetic data in this build)"
BURST_WINDOW_S = 10 * 60
RATE_PER_MINUTE = 3
RATE_PER_DAY = 10
LOCK_TIMEOUT_S = 0.5
WORDING = "Pseudonymisation, not anonymity: identifiers are stored only as keyed hashes."

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    indicator_hash TEXT NOT NULL,
    indicator_type TEXT NOT NULL,
    reporter_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (indicator_hash, reporter_hash)
);
CREATE INDEX IF NOT EXISTS ix_reports_indicator ON reports (indicator_hash);
CREATE TABLE IF NOT EXISTS reporter_activity (reporter_hash TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_activity ON reporter_activity (reporter_hash, at);
CREATE TABLE IF NOT EXISTS reviews (
    indicator_hash TEXT PRIMARY KEY,
    decision TEXT NOT NULL CHECK (decision IN ('confirmed', 'rejected')),
    reviewer TEXT NOT NULL,
    at REAL NOT NULL
);
"""


def load_secret() -> bytes | None:
    s = os.environ.get("VERIQ_REGISTRY_SECRET")
    if not s and os.environ.get("VERIQ_REGISTRY_SECRET_FILE"):
        try:
            s = Path(os.environ["VERIQ_REGISTRY_SECRET_FILE"]).read_text(encoding="utf-8").strip()
        except OSError:
            s = None
    if not s or len(s.encode()) < 16:
        return None
    return s.encode()


def new_reporter_token() -> str:
    """One per user session. Kept only in the session; the registry stores a keyed hash of it."""
    return secrets.token_urlsafe(24)


@dataclass(frozen=True)
class ReportOutcome:
    status: str  # recorded | duplicate | rate_limited | excluded | unavailable
    note: str = ""


def create_db(path: str | os.PathLike) -> None:
    con = sqlite3.connect(str(path))
    try:
        con.executescript(SCHEMA)
        con.commit()
    finally:
        con.close()


class SQLiteRegistry:
    def __init__(self, db_path: str | os.PathLike, secret: bytes | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.db_path = Path(db_path)
        self.secret = secret if secret is not None else load_secret()
        self.clock = clock

    # -- plumbing --------------------------------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        if self.secret is None or len(self.secret) < 16:
            raise sqlite3.OperationalError("no registry secret configured")
        if not self.db_path.is_file():
            raise sqlite3.OperationalError("registry database missing")
        uri = f"{self.db_path.resolve().as_uri()}?mode=rw"
        con = sqlite3.connect(uri, uri=True, timeout=LOCK_TIMEOUT_S)
        con.execute("SELECT 1 FROM reports LIMIT 1")  # fails if the file is not a registry
        return con

    def _h(self, indicator_type: str, value_norm: str) -> str:
        return hmac_indicator(self.secret, indicator_type, value_norm)

    def _reporter(self, token: str) -> str:
        return hmac_indicator(self.secret, "reporter_token", token)

    # -- read ------------------------------------------------------------------------------------------------
    def independent_reporters(self, con: sqlite3.Connection, ih: str) -> tuple[int, int]:
        """(independent reporter clusters, raw distinct reporters) within the decay window."""
        since = self.clock() - DECAY_DAYS * 86400
        times = [r[0] for r in con.execute(
            "SELECT created_at FROM reports WHERE indicator_hash=? AND created_at>=? ORDER BY created_at", (ih, since))]
        clusters, last_start = 0, None
        for t in times:
            if last_start is None or t - last_start > BURST_WINDOW_S:
                clusters += 1
                last_start = t
        return clusters, len(times)

    def lookup(self, payee_id: str, indicator_type: str, value_norm: str) -> RegistryResult:
        if is_non_attributable(indicator_type, value_norm):
            return RegistryResult(payee_id, "unavailable", 0, False, SOURCE,
                                  "payment-gateway or aggregator handle: never stored, never linked")
        try:
            con = self._connect()
        except (sqlite3.Error, ValueError) as e:
            return RegistryResult(payee_id, "unavailable", 0, False, SOURCE, f"registry unavailable ({e})")
        try:
            ih = self._h(indicator_type, value_norm)
            n, raw = self.independent_reporters(con, ih)
            row = con.execute("SELECT decision FROM reviews WHERE indicator_hash=?", (ih,)).fetchone()
        except sqlite3.Error as e:
            return RegistryResult(payee_id, "unavailable", 0, False, SOURCE, f"registry unavailable ({e})")
        finally:
            con.close()
        review = row[0] if row else None
        if review == "rejected":
            return RegistryResult(payee_id, "clean", n, False, SOURCE,
                                  f"{raw} report(s) rejected by a reviewer as false; not linked")
        if review == "confirmed" or n >= LINK_MIN_INDEPENDENT_REPORTERS:
            why = "confirmed by a reviewer" if review == "confirmed" else f"{n} independent reporters"
            return RegistryResult(payee_id, "linked", n, review == "confirmed", SOURCE, f"linked: {why}")
        note = "no reports in this registry. This does not mean the payee is safe." if raw == 0 else (
            f"{raw} report(s) from {n} independent reporter(s); not enough to link"
            + ("; several reports arrived together, so they count once until a reviewer looks" if raw > n else ""))
        return RegistryResult(payee_id, "clean", n, False, SOURCE, note)

    # -- write -----------------------------------------------------------------------------------------------
    def report(self, indicator_type: str, value_norm: str, reporter_token: str) -> ReportOutcome:
        """Record that this session's user reports this payee. Only hashes are stored."""
        if is_non_attributable(indicator_type, value_norm):
            return ReportOutcome("excluded", "payment-gateway or aggregator handle: not stored")
        try:
            con = self._connect()
        except (sqlite3.Error, ValueError) as e:
            return ReportOutcome("unavailable", str(e))
        try:
            now = self.clock()
            rh = self._reporter(reporter_token)
            last_min = con.execute("SELECT COUNT(*) FROM reporter_activity WHERE reporter_hash=? AND at>?",
                                   (rh, now - 60)).fetchone()[0]
            last_day = con.execute("SELECT COUNT(*) FROM reporter_activity WHERE reporter_hash=? AND at>?",
                                   (rh, now - 86400)).fetchone()[0]
            if last_min >= RATE_PER_MINUTE or last_day >= RATE_PER_DAY:
                return ReportOutcome("rate_limited", "too many reports from this session; try later")
            con.execute("INSERT INTO reporter_activity (reporter_hash, at) VALUES (?, ?)", (rh, now))
            cur = con.execute("INSERT OR IGNORE INTO reports (indicator_hash, indicator_type, reporter_hash, created_at) "
                              "VALUES (?, ?, ?, ?)", (self._h(indicator_type, value_norm), indicator_type, rh, now))
            con.commit()
            return ReportOutcome("recorded" if cur.rowcount == 1 else "duplicate",
                                 "" if cur.rowcount == 1 else "this session already reported this payee")
        except sqlite3.Error as e:
            return ReportOutcome("unavailable", str(e))
        finally:
            con.close()

    def review(self, indicator_type: str, value_norm: str, decision: str, reviewer: str) -> ReportOutcome:
        """Reviewer confirms or rejects a payee's reports (fed by the reviewer console)."""
        if decision not in ("confirmed", "rejected"):
            raise ValueError("decision must be 'confirmed' or 'rejected'")
        if is_non_attributable(indicator_type, value_norm):
            return ReportOutcome("excluded", "payment-gateway or aggregator handle: never linked")
        try:
            con = self._connect()
        except (sqlite3.Error, ValueError) as e:
            return ReportOutcome("unavailable", str(e))
        try:
            con.execute("INSERT OR REPLACE INTO reviews (indicator_hash, decision, reviewer, at) VALUES (?, ?, ?, ?)",
                        (self._h(indicator_type, value_norm), decision, reviewer[:60], self.clock()))
            con.commit()
            return ReportOutcome("recorded")
        except sqlite3.Error as e:
            return ReportOutcome("unavailable", str(e))
        finally:
            con.close()


def from_env() -> SQLiteRegistry | None:
    """The app uses the SQLite registry only when VERIQ_REGISTRY_DB names an existing file and a secret is set."""
    p = os.environ.get("VERIQ_REGISTRY_DB")
    if not p:
        return None
    return SQLiteRegistry(p)
