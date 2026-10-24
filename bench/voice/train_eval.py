"""Train and test VERIQ's voice check on the finale voice set (bench/voice/make_set.py). FINALE, Claude C.

Two detectors, same held-out TEST split (speakers and voices never seen in train or dev):
  A. "pretrained": AASIST as published (Claude B's voice.detector.AasistDetector), raw bonafide logit.
  B. "trained head": a logistic-regression classifier we TRAIN on AASIST's 160-dim embeddings (train split only).
Thresholds for both are fixed on the DEV split so that at most 5% of genuine dev clips are flagged (brief section 7).
TEST is used once, for reporting. Bootstrap 95% intervals are given because the test set is small.

Usage: python -m bench.voice.train_eval --data <voiceset dir> --aasist <aasist repo dir> [--out bench/voice/results.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf

FAR = 0.05
RNG = np.random.default_rng(20261024)


def load_detector(repo):
    from voice.detector import AasistDetector
    return AasistDetector(repo_dir=repo)


def features(det, path):
    """EXACTLY the product preprocessing (Claude B's voice.pipeline): ffmpeg decode to 16 kHz mono, quality gate,
    speech-only samples (VAD), fixed chunks. Returns None if the gate would abstain (cant_assess in the product),
    else (mean bonafide logit, mean 160-dim embedding)."""
    from voice.audio import TARGET_SR, decode_to_mono16k
    from voice.gate import GateConfig, run_gate
    from voice.pipeline import make_chunks
    from voice.vad import speech_mask, speech_samples
    x = decode_to_mono16k(path)
    if not run_gate(x, GateConfig(), TARGET_SR).passed:
        return None
    mask, flen = speech_mask(x, TARGET_SR)
    sp = speech_samples(x, mask, flen)
    chunks = make_chunks(sp if sp.size >= TARGET_SR // 4 else x, det.chunk_samples, 12)
    torch = det._torch
    with torch.no_grad():
        t = torch.from_numpy(np.stack(chunks)).to(det._device)
        hidden, logits = det._model(t)
    return float(logits[:, 1].mean()), hidden.mean(0).cpu().numpy()


def roc_auc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s))


def eer(y, s):
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y, s)
    i = np.nanargmin(np.abs((1 - tpr) - fpr))
    return float((fpr[i] + (1 - tpr[i])) / 2)


def thr_at_far(fake_score_real_clips, far=FAR):
    """'fake score' higher = more fake. Threshold so <= far of genuine dev clips are at or above it."""
    s = np.sort(np.asarray(fake_score_real_clips))
    k = int(np.floor(far * len(s)))
    return float(s[len(s) - k - 1] + 1e-9) if k < len(s) else float(s[-1])


def rates(y, s, thr):
    y, s = np.asarray(y), np.asarray(s)
    flagged = s > thr
    return float(flagged[y == 0].mean()), float(flagged[y == 1].mean())


def boot(y, s, thr, n=2000):
    y, s = np.asarray(y), np.asarray(s)
    gf, fc = [], []
    for _ in range(n):
        i = RNG.integers(0, len(y), len(y))
        if len(set(y[i])) < 2:
            continue
        a, b = rates(y[i], s[i], thr)
        gf.append(a)
        fc.append(b)
    return [round(float(np.percentile(gf, 2.5)), 3), round(float(np.percentile(gf, 97.5)), 3)], \
           [round(float(np.percentile(fc, 2.5)), 3), round(float(np.percentile(fc, 97.5)), 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--aasist", required=True)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results.json"))
    a = ap.parse_args()
    root = Path(a.data)
    rows = list(csv.DictReader(open(root / "labels.csv", encoding="utf-8")))
    det = load_detector(a.aasist)
    t0 = time.perf_counter()
    abstained = []
    for r in rows:
        f = features(det, str(root / r["file"]))
        if f is None:
            abstained.append(r)
        else:
            r["raw"], r["emb"] = f
    secs = (time.perf_counter() - t0) / len(rows)
    rows = [r for r in rows if "emb" in r]

    def part(split, lang=None):
        sel = [r for r in rows if r["split"] == split and (lang is None or r["lang"] == lang)]
        return sel, np.array([1 if r["label"] == "fake" else 0 for r in sel])

    tr, ytr = part("train")
    dv, ydv = part("dev")
    te, yte = part("test", "en")
    hi, _ = part("test", "hi")

    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    head = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
    head.fit(np.stack([r["emb"] for r in tr]), ytr)

    out = {"model_version": det.model_version, "data": str(root.name), "far_target_on_dev": FAR,
           "n": {"train": len(tr), "dev": len(dv), "test_en": len(te), "test_hindi_fake_only": len(hi)},
           "seconds_per_clip_cpu": round(secs, 3),
           "preprocessing": "same as product: ffmpeg decode, quality gate, speech-only (VAD), 4 s chunks",
           "gate_abstained": {"count": len(abstained), "by_split_label": {f"{s_}/{l_}": sum(1 for r in abstained if r["split"] == s_ and r["label"] == l_)
                                                                         for s_ in ("train", "dev", "test") for l_ in ("real", "fake")}},
           "detectors": {}}
    for name, fn in (("pretrained", lambda S: np.array([-r["raw"] for r in S])),
                     ("trained_head", lambda S: head.predict_proba(np.stack([r["emb"] for r in S]))[:, 1])):
        sdv, ste, shi = fn(dv), fn(te), fn(hi) if hi else np.array([])
        thr = thr_at_far(sdv[ydv == 0])
        gf, fc = rates(yte, ste, thr)
        ci_gf, ci_fc = boot(yte, ste, thr)
        per = {}
        for r, s in zip(te, ste):
            per.setdefault(r["source"], []).append(bool(s > thr))
        fails = sorted([{"source": k, "label": next(r["label"] for r in te if r["source"] == k),
                         "flagged_rate": round(sum(v) / len(v), 2)} for k, v in per.items()],
                       key=lambda d: d["flagged_rate"])
        out["detectors"][name] = {
            "dev_auc": round(roc_auc(ydv, sdv), 3), "dev_eer": round(eer(ydv, sdv), 3),
            "test_auc": round(roc_auc(yte, ste), 3), "test_eer": round(eer(yte, ste), 3),
            "test_genuine_flagged": round(gf, 3), "test_genuine_flagged_95ci": ci_gf,
            "test_synthetic_caught": round(fc, 3), "test_synthetic_caught_95ci": ci_fc,
            "hindi_synthetic_caught": round(float((shi > thr).mean()), 3) if len(shi) else None,
            "per_source_on_test": fails}
    # Export the trained head (plain JSON, no pickle) and its dev-fitted threshold for app/adapters/voice_head.py
    sc, lr = head.named_steps["standardscaler"], head.named_steps["logisticregression"]
    params = {"kind": "logistic_regression_on_aasist_embedding", "base_model_version": det.model_version,
              "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(), "coef": lr.coef_[0].tolist(),
              "intercept": float(lr.intercept_[0]), "trained_on": "bench/voice/make_set.py train split (24 Oct 2026)"}
    head_path = Path(a.out).with_name("head.json")
    head_path.write_text(json.dumps(params), encoding="utf-8")
    import hashlib
    hv = hashlib.sha256(head_path.read_bytes()).hexdigest()[:12]
    sdv = head.predict_proba(np.stack([r["emb"] for r in dv]))[:, 1]
    cal = {"threshold": thr_at_far(sdv[ydv == 0]), "polarity": "higher_is_fake", "score_kind": "calibrated",
           "model_version": f"{det.model_version}+head@{hv}", "target_false_alarm": FAR,
           "calibrated_on": "bench/voice/make_set.py dev split (2 FSDD speakers, 8 Kokoro voices, Opus 16k), 24 Oct 2026"}
    Path(a.out).with_name("head_calibration.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
    out["exported"] = {"head": head_path.name, "calibration": "head_calibration.json", "model_version": cal["model_version"]}
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
