#!/usr/bin/env python3
"""Tidy the repository WITHOUT rewriting history (run once on the laptop after copying a delivery over the repo).

    python scripts/tidy_repo.py            # shows what it will do, then does it with `git mv` / `git rm`
    python scripts/tidy_repo.py --dry-run

Internal working notes from the build (cross-team handoffs, change requests, superseded demo/Q&A drafts) move to
docs/history/ so the top level shows only what judges need. Nothing is deleted from git history; no rebase, reset or
force-push. Safe to run twice.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOVES = [
    ("HANDOFF_B_to_C.md", "docs/history/HANDOFF_B_to_C.md"),
    ("HANDOFF_B_FINAL.md", "docs/history/HANDOFF_B_FINAL.md"),
    ("CHANGES_REQUESTED.md", "docs/history/CHANGES_REQUESTED.md"),
    ("voice/B_RESULTS_ROWS.md", "docs/history/B_RESULTS_ROWS.md"),
    ("voice/B_DOC_UPDATES.md", "docs/history/B_DOC_UPDATES.md"),
    ("app/DEMO.md", "docs/history/DEMO_v1.md"),
    ("docs/QA.md", "docs/history/QA_v1.md"),
]


def tracked(path: str) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", path], cwd=ROOT, capture_output=True).returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT, capture_output=True).returncode != 0:
        print("not a git repository")
        return 1
    for src, dst in MOVES:
        s, d = ROOT / src, ROOT / dst
        if not s.exists():
            print(f"ok      {src} (already moved)")
            continue
        if d.exists():
            cmd = ["git", "rm", "-q", "--", src] if tracked(src) else None
            what = f"remove  {src} (its copy is already at {dst})"
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            cmd = ["git", "mv", src, dst] if tracked(src) else None
            what = f"move    {src} -> {dst}"
            if cmd is None:
                s.rename(d)
        print(what)
        if cmd and not a.dry_run:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                print("   failed:", r.stderr.strip())
                return 1
        elif cmd is None and d.exists() and s.exists() and not a.dry_run:
            s.unlink()
    print("done (no history rewritten)" if not a.dry_run else "dry run: nothing changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
