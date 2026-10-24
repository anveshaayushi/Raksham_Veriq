"""Tiny SYNTHETIC seed for the SQLite registry (Claude C, until Claude A's registry seed file arrives).

Usage (from veriq/):
    set VERIQ_REGISTRY_SECRET=<at least 16 characters>      (PowerShell: $env:VERIQ_REGISTRY_SECRET="...")
    python -m registry.seed registry_demo.db
All identifiers are fictional. Each seeded report uses its own throwaway reporter token, spaced in time so they
count as independent reporters.
"""

from __future__ import annotations

import sys
import time

from .sqlite_registry import BURST_WINDOW_S, SQLiteRegistry, create_db, load_secret, new_reporter_token

# (indicator_type, value_norm, number of independent synthetic reporters)
SEED = [
    ("upi_vpa", "fixture.linked@upi", 3),      # linked
    ("upi_vpa", "sunita.t@upi", 2),            # linked: Scenario A's second payee, a "known pattern" for the demo
    ("bank_account", "30112233445021", 1),     # one report: not linked
]


def seed(db_path: str, secret: bytes, start: float | None = None) -> None:
    create_db(db_path)
    t = [start if start is not None else time.time() - 30 * 86400]

    def clock() -> float:
        return t[0]

    reg = SQLiteRegistry(db_path, secret=secret, clock=clock)
    for itype, value, n in SEED:
        for _ in range(n):
            out = reg.report(itype, value, new_reporter_token())
            assert out.status == "recorded", out
            t[0] += BURST_WINDOW_S + 3600


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    secret = load_secret()
    if secret is None:
        print("Set VERIQ_REGISTRY_SECRET (16+ characters) first.")
        return 2
    seed(argv[1], secret)
    print(f"Seeded {argv[1]} with {sum(n for *_, n in SEED)} synthetic reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
