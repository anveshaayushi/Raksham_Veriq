#!/usr/bin/env python3
"""Dataset registry + licence/access bookkeeping (brief sections 7, 19; rule 14.1-14.3).

THIS SCRIPT DOWNLOADS NOTHING AND ASSERTS NO LICENCES. Licence and access terms below are marked
UNVERIFIED on purpose: Claude B had no internet access to the dataset pages when drafting. A human opens each
source, reads the terms, and records what they saw with the `record` command. `disclosure` then prints the
DISCLOSURE.md table from those records only.

    python scripts/datasets.py list
    python scripts/datasets.py status
    python scripts/datasets.py record asvspoof2019_la --source-url <url you opened> \
        --licence "<exact licence text/name you read>" --allowed train,dev --checked-by anvesha --notes "..."
    python scripts/datasets.py disclosure

Downloaded data goes under data/raw/<name>/ (git-ignored). Role "test-only" means never train or tune on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# role: how the brief says to use it. pointer: where the brief itself points (no URLs invented here).
REGISTRY = {
    "asvspoof2019_la": {"role": "train/dev", "pointer": "ASVspoof 2019 LA (brief s7); find the official data page via the ASVspoof challenge site"},
    "asvspoof5": {"role": "train/dev (if feasible)", "pointer": "ASVspoof 5 (brief s7); very large, check size vs disk first"},
    "mlaad": {"role": "train/dev", "pointer": "arXiv:2401.09512 (multilingual TTS fakes)"},
    "sea_spoof": {"role": "dev/test (Hindi)", "pointer": "arXiv:2509.19865 (includes Hindi)"},
    "hav_df": {"role": "dev/test (Hindi audio-video)", "pointer": "arXiv:2411.15457"},
    "in_the_wild": {"role": "test-only", "pointer": "In-the-Wild audio deepfake set (brief s7: TEST ONLY)"},
    "common_voice_hi": {"role": "genuine Hindi speech (dev)", "pointer": "Mozilla Common Voice Hindi; brief says verify availability"},
    "deepfake_eval_2024": {"role": "test-only", "pointer": "github.com/nuriachandra/Deepfake-Eval-2024 (brief s19); arXiv:2503.02857"},
    "own_consented_voices": {"role": "dev/test", "pointer": "team members, written consent, labelled synthetic where cloned"},
    "own_tts_clones": {"role": "dev/test", "pointer": "open TTS with a licence that allows this use; never of real public figures"},
}


def _rec_path(name: str) -> Path:
    return RAW / name / "LICENCE_CHECK.json"


def cmd_list(_):
    for k, v in REGISTRY.items():
        print(f"{k:22s} role={v['role']:32s} licence=UNVERIFIED  {v['pointer']}")


def cmd_status(_):
    print(f"{'dataset':22s} {'data dir':9s} {'licence recorded':16s}")
    for k in REGISTRY:
        d = RAW / k
        has_dir = d.is_dir() and any(p for p in d.iterdir() if p.name != "LICENCE_CHECK.json")
        print(f"{k:22s} {'yes' if has_dir else 'no':9s} {'yes' if _rec_path(k).is_file() else 'NO - do not use yet':16s}")


def cmd_record(a):
    if a.name not in REGISTRY:
        sys.exit(f"unknown dataset {a.name}; see `list`")
    p = _rec_path(a.name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "name": a.name, "source_url": a.source_url, "licence_as_read": a.licence,
        "allowed_uses": [x for x in a.allowed.split(",") if x], "checked_by": a.checked_by,
        "date": date.today().isoformat(), "notes": a.notes, "role_per_brief": REGISTRY[a.name]["role"],
    }, indent=2), encoding="utf-8")
    print(f"recorded {p}")


def cmd_disclosure(_):
    print("| Dataset | Role | Source | Licence (as read by team) | Allowed uses | Checked by / date |")
    print("|---|---|---|---|---|---|")
    for k in REGISTRY:
        p = _rec_path(k)
        if p.is_file():
            r = json.loads(p.read_text(encoding="utf-8"))
            print(f"| {k} | {r['role_per_brief']} | {r['source_url']} | {r['licence_as_read']} | {', '.join(r['allowed_uses'])} | {r['checked_by']} {r['date']} |")
        else:
            print(f"| {k} | {REGISTRY[k]['role']} | not recorded | UNVERIFIED | not cleared for use | - |")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("list").set_defaults(f=cmd_list)
    sp.add_parser("status").set_defaults(f=cmd_status)
    sp.add_parser("disclosure").set_defaults(f=cmd_disclosure)
    r = sp.add_parser("record")
    r.add_argument("name")
    r.add_argument("--source-url", required=True)
    r.add_argument("--licence", required=True)
    r.add_argument("--allowed", required=True, help="comma list from: train,dev,test")
    r.add_argument("--checked-by", required=True)
    r.add_argument("--notes", default="")
    r.set_defaults(f=cmd_record)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
