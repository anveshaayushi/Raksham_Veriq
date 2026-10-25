"""veriq-eval: batch-score a folder of files (brief sections 11 and 20).

    ./veriq-eval --input <folder> --out preds.csv [--json] [--calibration cal.json]
                 [--aasist-repo DIR] [--labels labels.csv | --infer-labels-from-dirs]

Guarantees: one row per file found; never crashes on a bad file (it becomes cant_assess + reason);
exit code 0 unless the command line itself is unusable (exit 2).

Every media row reports BOTH `state` (flagged / no_signal / cant_assess, the product's honest answer,
abstentions included) AND `pred_label` (forced fake/real from the calibrated threshold, no abstention)
plus the raw `score`, so organisers can apply their own metric. `pred_label` is empty when no valid
calibration exists for the loaded model. Abstention rate is reported separately in the summary.

Not handled here (Claude A's / later work): chat parsing, zip unpacking, image forensics, video frames.
Those rows are emitted as cant_assess with an explicit reason, never silently dropped.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eval import metrics as M
from voice.audio import sha256_file
from voice.calibration import Calibration, CalibrationError, load_calibration
from voice.gate import GateConfig
from voice.pipeline import assess_audio_file

AUDIO_EXT = {".wav", ".mp3", ".opus", ".ogg", ".m4a", ".flac", ".aac", ".amr", ".wma"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CHAT_EXT = {".txt", ".csv", ".json"}
ARCHIVE_EXT = {".zip"}
REAL_WORDS = {"real", "bonafide", "bona-fide", "genuine", "authentic", "legit", "legitimate", "ham"}
FAKE_WORDS = {"fake", "spoof", "deepfake", "synthetic", "tts", "clone", "cloned", "scam", "fraud", "spam"}
GROUP_COLS = ("dataset", "codec", "language")
FIELDS = ["file_id", "path", "sha256", "modality", "state", "pred_label", "score", "threshold",
          "score_kind", "speech_seconds", "reasons", "model_version", "elapsed_s", "label",
          "dataset", "codec", "language"]


def build_detector(args) -> Tuple[Optional[object], Optional[str]]:
    if args.detector == "none":
        return None, "detector disabled (--detector none)"
    try:
        from voice.detector import AasistDetector

        base = AasistDetector(repo_dir=args.aasist_repo, weights=args.aasist_weights)
        if args.detector == "head":  # VERIQ's trained head on AASIST embeddings (app/adapters/voice_head.py)
            from app.adapters.voice_head import load_head
            det, cal = load_head(base)
            if not args.calibration:
                args.head_calibration = cal  # the head's own threshold, fixed on its FSDD/Kokoro dev split
            return det, None
        return base, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:200]


def _norm_label(s: str) -> Optional[str]:
    w = s.strip().lower()
    return "real" if w in REAL_WORDS else "fake" if w in FAKE_WORDS else None


def _read_labels(path: Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("file"):
                out[row["file"].replace("\\", "/")] = row
    return out


def _infer_from_dirs(rel: str) -> Optional[str]:
    for part in Path(rel).parts[:-1]:
        lab = _norm_label(part)
        if lab:
            return lab
    return None


def _row(**kw) -> dict:
    r = {k: "" for k in FIELDS}
    r.update(kw)
    return r


def evaluate_folder(root: Path, detector, det_err, calibration: Optional[Calibration],
                    labels: Dict[str, dict], infer_dirs: bool, timeout_s: float) -> List[dict]:
    rows: List[dict] = []
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = f.relative_to(root).as_posix()
        if any(part.startswith(".") for part in f.relative_to(root).parts):
            continue
        if f.name.lower() in {"labels.csv", "labels.json"}:
            continue
        ext = f.suffix.lower()
        try:
            sha = sha256_file(f)
        except OSError:
            sha = ""
        lab_row = labels.get(rel, {})
        label = _norm_label(lab_row.get("label", "")) if lab_row else None
        if label is None and infer_dirs:
            label = _infer_from_dirs(rel)
        extra = {"label": label or "", **{c: lab_row.get(c, "") for c in GROUP_COLS}}

        if ext in AUDIO_EXT or ext in VIDEO_EXT:
            modality = "video" if ext in VIDEO_EXT else "audio"
            a = assess_audio_file(f, detector, calibration, GateConfig(), file_id=rel,
                                  force_score=True, decode_timeout_s=timeout_s, detector_error=det_err)
            r = a.result
            reasons = list(r.reasons)
            if modality == "video":
                reasons.append("video: audio track only; no visual analysis")
            rows.append(_row(file_id=rel, path=str(f), sha256=sha, modality=modality, state=r.state,
                             pred_label=a.pred_label or "", score=("" if r.score is None else f"{r.score:.6f}"),
                             threshold=("" if r.threshold is None else r.threshold), score_kind=a.score_kind,
                             speech_seconds=r.speech_seconds, reasons=" | ".join(reasons),
                             model_version=r.model_version, elapsed_s=f"{a.elapsed_s:.3f}", **extra))
            continue
        # a kit's own notes (README.txt, LICENSE, NOTES.md) keep their row (one row per file) but are not scored as chats
        if re.match(r"(readme|license|licence|notes|manifest)(\.(txt|md))?$", f.name.lower()):
            rows.append(_row(file_id=rel, path=str(f), sha256=sha, modality="other", state="cant_assess",
                             reasons="kit notes file (README/LICENSE), not an input", **extra))
            continue
        if ext in IMAGE_EXT or ext in ARCHIVE_EXT or ext == ".txt":  # Q3 kit runner: eval/kit.py
            from eval import kit
            mod = "image" if ext in IMAGE_EXT else "chat"
            fn = kit.image_assessment if mod == "image" else (lambda p, lr=lab_row: kit.chat_assessment(p, lr))
            k = kit.with_timeout(fn, max(timeout_s, 10.0) * 2, f)
            rows.append(_row(file_id=rel, path=str(f), sha256=sha, modality=mod, state=k["state"],
                             pred_label=k.get("pred_label", ""), reasons=" | ".join(k["reasons"]),
                             model_version="veriq-rules" if mod == "chat" else "qr-only", **extra))
            continue
        if ext in CHAT_EXT:
            why, mod = "not_a_whatsapp_export: only .txt and WhatsApp .zip chats are read", "chat"
        else:
            why, mod = f"unsupported_extension({ext or 'none'})", "unknown"
        rows.append(_row(file_id=rel, path=str(f), sha256=sha, modality=mod, state="cant_assess",
                         reasons=why, model_version="n/a", **extra))
    return rows


def summarize(rows: List[dict], polarity: Optional[str]) -> dict:
    media = [r for r in rows if r["modality"] in ("audio", "video")]
    s = {
        "n_files": len(rows),
        "by_modality": dict(Counter(r["modality"] for r in rows)),
        "by_state_media": dict(Counter(r["state"] for r in media)),
        "abstention_rate_media": (sum(r["state"] == "cant_assess" for r in media) / len(media)) if media else None,
    }
    lab = [r for r in media if r["label"] in ("real", "fake") and r["score"] != ""]
    if lab and polarity:
        sign = -1.0 if polarity == "higher_is_real" else 1.0

        def block(rs: List[dict]) -> dict:
            fk = [sign * float(r["score"]) for r in rs if r["label"] == "fake"]
            rl = [sign * float(r["score"]) for r in rs if r["label"] == "real"]
            rt = M.rates([r["label"] for r in rs], [r["pred_label"] or None for r in rs])
            return {"n": len(rs), "auc": M.auc(fk, rl), "eer": M.eer(fk, rl),
                    "false_alarm_at_threshold": rt["false_alarm"], "miss_at_threshold": rt["miss"],
                    "abstained": sum(r["state"] == "cant_assess" for r in rs)}

        s["metrics_all_labelled"] = block(lab)
        for col in GROUP_COLS:
            vals = sorted({r[col] for r in lab if r[col]})
            if vals:
                s[f"metrics_by_{col}"] = {v: block([r for r in lab if r[col] == v]) for v in vals}
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="veriq-eval", description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true", help="also write <out>.json with the same records")
    ap.add_argument("--detector", choices=["aasist", "head", "none"], default="aasist",
                    help="aasist = pretrained AASIST; head = AASIST + VERIQ's trained head (uses its own calibration)")
    ap.add_argument("--aasist-repo", default=os.environ.get("VERIQ_AASIST_REPO"))
    ap.add_argument("--aasist-weights", default=None)
    ap.add_argument("--calibration", default=None, help="calibration JSON (see voice/calibration.py)")
    ap.add_argument("--labels", default=None, help="CSV with columns file,label[,dataset,codec,language]")
    ap.add_argument("--infer-labels-from-dirs", action="store_true",
                    help="HEURISTIC: treat a parent folder named real/fake/bonafide/spoof/... as the label")
    ap.add_argument("--timeout", type=float, default=30.0, help="per-file time limit in seconds (decode / chat)")
    ap.add_argument("--report", default=None, help="also write a Markdown judge report (eval/kit.py)")
    args = ap.parse_args(argv)

    root = Path(args.input)
    if not root.is_dir():
        print(f"error: --input {root} is not a folder", file=sys.stderr)
        return 2

    detector, det_err = build_detector(args)
    if det_err:
        print(f"warning: no detector ({det_err}); media rows will be cant_assess", file=sys.stderr)
    calibration = getattr(args, "head_calibration", None)
    if not args.calibration and calibration is None and args.detector == "aasist":
        from app.config import voice_calibration_path
        args.calibration = voice_calibration_path()  # weak-cue threshold (ASVspoof LA dev); VERIQ_VOICE_CALIBRATION=none disables
        if args.calibration:
            print(f"note: using voice threshold {args.calibration} (weak review cue)", file=sys.stderr)
    if args.calibration:
        try:
            calibration = load_calibration(args.calibration)
        except CalibrationError as e:
            print(f"warning: {e}; running uncalibrated", file=sys.stderr)
    labels = {}
    if args.labels:
        try:
            labels = _read_labels(Path(args.labels))
        except OSError as e:
            print(f"warning: cannot read labels: {e}", file=sys.stderr)

    rows = evaluate_folder(root, detector, det_err, calibration, labels,
                           args.infer_labels_from_dirs, args.timeout)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    if args.json:
        recs = []
        for r in rows:
            d = dict(r)
            d["score"] = None if r["score"] == "" else float(r["score"])
            d["threshold"] = None if r["threshold"] == "" else float(r["threshold"])
            d["reasons"] = [x for x in r["reasons"].split(" | ") if x]
            d["components"] = []
            recs.append(d)
        out.with_suffix(".json").write_text(json.dumps(recs, indent=2), encoding="utf-8")

    polarity = (calibration.polarity if calibration else getattr(detector, "native_polarity", None))
    summary = summarize(rows, polarity)
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), file=sys.stderr)
    if args.report:
        from eval.kit import build_report
        cmd = "veriq-eval " + " ".join(argv if argv is not None else sys.argv[1:])
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(build_report(rows, cmd, polarity), encoding="utf-8")
        print(f"report: {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
