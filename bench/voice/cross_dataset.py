"""Cross-dataset voice evaluation and a retrained head (Q2 item a). FINALE, Claude C, 25 Oct 2026.

Data (all scored through the SAME product preprocessing: ffmpeg decode, quality gate, speech-only VAD, 4 s chunks):
  V  = our voice set (bench/voice/make_set.py): FSDD real speakers (6) vs Kokoro TTS voices (28); Opus 16 kbit/s.
  AD = ASVspoof 2019 LA dev subset (Claude B's bundle): 60 real + 60 spoof base clips x {clean, mp3, opus}.
       Spoofs use attacks A01-A06 (the same attack types as LA train).
  AE = ASVspoof 2019 LA eval subset (Claude B's bundle): 100 real + 100 spoof base clips x {clean, mp3, opus}.
       Eval speakers differ from dev speakers, and eval spoofs use attacks A07-A19 (mostly unseen in train/dev).
AE is NEVER used to train or to choose a threshold. It is scored once per model, for reporting.

Models compared:
  pretrained   AASIST as published (it was TRAINED on LA train: LA numbers are in-distribution for it)
  head_v1      the head shipped in the app (trained on V train; threshold from V dev), unchanged
  head_v2      logistic regression on AASIST embeddings, trained on V train+dev AND AD (two kinds of real
               speakers, Kokoro + six LA attack systems). Threshold chosen by 5-fold GROUPED cross-validation on its
               own training data (groups = speaker / voice / base clip, so codec copies never straddle folds) to
               flag at most 5% of genuine clips. Exported to bench/voice/v2/ but NOT installed in the app.

    python -m bench.voice.cross_dataset --voiceset <dir> --asv-dev data/subsets/dev --asv-eval data/subsets/eval \
        --aasist external/aasist --out results/voice_xd
Writes results.json, a Markdown table, per-file scores (scores.csv), and the v2 head files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

FAR = 0.05
SEED = 20261025


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def auc_eer(y, s):
    from sklearn.metrics import roc_auc_score, roc_curve
    y, s = np.asarray(y), np.asarray(s)
    if len(set(y.tolist())) < 2:
        return None, None
    fpr, tpr, _ = roc_curve(y, s)
    i = int(np.nanargmin(np.abs((1 - tpr) - fpr)))
    return round(float(roc_auc_score(y, s)), 3), round(float((fpr[i] + 1 - tpr[i]) / 2), 3)


def thr_at_far(genuine_scores, far=FAR):
    s = np.sort(np.asarray(genuine_scores))
    k = int(np.floor(far * len(s)))
    return float(s[len(s) - k - 1] + 1e-9)


def block(rows, score_key, thr):
    """rows: dicts with label (1 = fake), score_key; thr: flag if score > thr (higher = more fake)."""
    lab = [r for r in rows if r.get(score_key) is not None]
    y = [r["y"] for r in lab]
    s = [r[score_key] for r in lab]
    auc, eer = auc_eer(y, s)
    g = [r for r in lab if r["y"] == 0]
    f = [r for r in lab if r["y"] == 1]
    gf = sum(r[score_key] > thr for r in g) if thr is not None else None
    fc = sum(r[score_key] > thr for r in f) if thr is not None else None
    return {"n": len(lab), "n_real": len(g), "n_fake": len(f), "abstained_by_gate": len(rows) - len(lab),
            "auc": auc, "eer": eer,
            "genuine_flagged": round(gf / len(g), 3) if g and thr is not None else None,
            "genuine_flagged_wilson95": wilson(gf, len(g)) if thr is not None else None,
            "synthetic_caught": round(fc / len(f), 3) if f and thr is not None else None,
            "synthetic_caught_wilson95": wilson(fc, len(f)) if thr is not None else None}


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_rows(voiceset: Path | None, asv_dev: Path, asv_eval: Path) -> list[dict]:
    rows = []
    if voiceset:
        for r in csv.DictReader(open(voiceset / "labels.csv", encoding="utf-8")):
            rows.append({"path": voiceset / r["file"], "file": r["file"], "y": int(r["label"] == "fake"),
                         "data": "V", "split": r["split"], "group": "V:" + r["source"], "source": r["source"],
                         "codec": "opus16k", "lang": r["lang"]})
    for name, root in (("AD", asv_dev), ("AE", asv_eval)):
        for r in csv.DictReader(open(root / "labels.csv", encoding="utf-8")):
            base = re.sub(r"__\w+(?=\.wav$)", "", Path(r["file"]).name)
            rows.append({"path": root / r["file"], "file": r["file"], "y": int(r["label"] == "fake"), "data": name,
                         "split": name, "group": f"{name}:{base}", "source": f"asvspoof_{r['label']}",
                         "codec": r.get("codec", "clean"), "lang": r.get("language", "en")})
    return rows


def featurize(rows, aasist_repo: str, cache_path: Path):
    from bench.voice.train_eval import features, load_detector
    cache = {}
    if cache_path.is_file():
        z = np.load(cache_path, allow_pickle=False)
        cache = {k: z[k] for k in z.files}
    det = None
    for i, r in enumerate(rows):
        key = file_sha(r["path"])
        if key not in cache:
            if det is None:
                det = load_detector(aasist_repo)
            f = features(det, str(r["path"]))
            cache[key] = np.zeros(0) if f is None else np.concatenate([[f[0]], f[1]])
            if i % 100 == 0:
                np.savez(cache_path, **cache)
                print(f"  features {i}/{len(rows)}", flush=True)
        v = cache[key]
        r["raw"] = None if v.size == 0 else float(v[0])
        r["emb"] = None if v.size == 0 else v[1:]
    np.savez(cache_path, **cache)
    return det


def fit_head(train):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=4000))
    m.fit(np.stack([r["emb"] for r in train]), [r["y"] for r in train])
    return m


def cv_threshold(train, k=5):
    """Out-of-fold scores with folds by group (speaker / voice / base clip); threshold at FAR on genuine OOF."""
    from sklearn.model_selection import GroupKFold
    X = np.stack([r["emb"] for r in train])
    y = np.array([r["y"] for r in train])
    g = np.array([r["group"] for r in train])
    oof = np.zeros(len(train))
    for tr, te in GroupKFold(n_splits=k).split(X, y, g):
        m = fit_head([train[i] for i in tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    auc, eer = auc_eer(y, oof)
    return thr_at_far(oof[y == 0]), {"cv_auc": auc, "cv_eer": eer, "folds": k, "grouped_by": "speaker/voice/base clip"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voiceset", required=True)
    ap.add_argument("--asv-dev", required=True)
    ap.add_argument("--asv-eval", required=True)
    ap.add_argument("--aasist", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--export-dir", default=str(Path(__file__).resolve().parent / "v2"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_rows(Path(a.voiceset), Path(a.asv_dev), Path(a.asv_eval))
    det = featurize(rows, a.aasist, out / "embeddings_cache.npz")
    ok = [r for r in rows if r["emb"] is not None]
    for r in rows:
        r["pre"] = None if r["raw"] is None else -r["raw"]  # pretrained: higher logit = real, so negate

    # head_v1 (shipped): same maths as app/adapters/voice_head.py, on the mean embedding
    from app.adapters.voice_head import CAL, HEAD
    h1 = json.loads(HEAD.read_text())
    thr1 = json.loads(CAL.read_text())["threshold"]
    mean, scale, coef, b = np.array(h1["mean"]), np.array(h1["scale"]), np.array(h1["coef"]), h1["intercept"]
    for r in rows:
        r["v1"] = None if r["emb"] is None else float(1 / (1 + np.exp(-(((r["emb"] - mean) / scale) @ coef + b))))

    # head_v2: train on V train+dev + AD; threshold by grouped CV
    train = [r for r in ok if (r["data"] == "V" and r["split"] in ("train", "dev")) or r["data"] == "AD"]
    thr2, cvinfo = cv_threshold(train)
    m2 = fit_head(train)
    for r in rows:
        r["v2"] = None if r["emb"] is None else float(m2.predict_proba(r["emb"][None, :])[0, 1])

    # leave-one-dataset-out heads (each trained on ONE source of data, threshold by grouped CV on it)
    v_only = [r for r in ok if r["data"] == "V" and r["split"] in ("train", "dev")]
    ad_only = [r for r in ok if r["data"] == "AD"]
    thr_v, _ = cv_threshold(v_only)
    m_v = fit_head(v_only)
    thr_ad, _ = cv_threshold(ad_only)
    m_ad = fit_head(ad_only)
    for r in rows:
        r["v_only"] = None if r["emb"] is None else float(m_v.predict_proba(r["emb"][None, :])[0, 1])
        r["ad_only"] = None if r["emb"] is None else float(m_ad.predict_proba(r["emb"][None, :])[0, 1])

    # pretrained threshold: B's ASVspoof-dev threshold (raw logit -4.241993, higher = real) -> negated
    b_cal = json.loads((Path(__file__).resolve().parents[2] / "results" / "asvspoof" /
                        "calibration_asvspoof_dev.json").read_text())
    thr_pre = -float(b_cal["threshold"])

    sets = {"AE (ASVspoof eval, unseen attacks + speakers)": [r for r in rows if r["data"] == "AE"],
            "V test (FSDD/Kokoro held-out speakers/voices, English)": [r for r in rows if r["data"] == "V" and r["split"] == "test" and r["lang"] == "en"],
            "V test Hindi synthetic only": [r for r in rows if r["data"] == "V" and r["split"] == "test" and r["lang"] == "hi"]}
    models = {"pretrained AASIST (threshold: B's ASVspoof dev)": ("pre", thr_pre),
              "head_v1 as shipped (threshold: FSDD/Kokoro dev)": ("v1", thr1),
              "head trained on V only (threshold: grouped CV on V)": ("v_only", thr_v),
              "head trained on ASVspoof dev only (threshold: grouped CV on AD)": ("ad_only", thr_ad),
              "head_v2 trained on V + ASVspoof dev (threshold: grouped CV)": ("v2", thr2)}
    res = {"made": "2026-10-25", "seed_note": "LogisticRegression is deterministic; GroupKFold is deterministic",
           "model_version_base": getattr(det, "model_version", None) if det else "cached features",
           "far_target": FAR, "head_v2_cv": cvinfo,
           "n": {k: len(v) for k, v in sets.items()}, "train_n": {"head_v2": len(train), "v_only": len(v_only),
                                                                 "ad_only": len(ad_only)},
           "results": {}}
    for sname, srows in sets.items():
        for mname, (key, thr) in models.items():
            r_all = block(srows, key, thr)
            res["results"].setdefault(sname, {})[mname] = {"all": r_all}
            if sname.startswith("AE"):
                for c in ("clean", "mp3", "opus"):
                    res["results"][sname][mname][c] = block([r for r in srows if r["codec"] == c], key, thr)
    # failure cases for head_v2 on AE: genuine flagged with the highest scores, spoofs missed with the lowest
    ae = [r for r in rows if r["data"] == "AE" and r["v2"] is not None]
    res["head_v2_AE_failures"] = {
        "genuine_flagged_top": [{"file": r["file"], "score": round(r["v2"], 3)} for r in
                                sorted([r for r in ae if r["y"] == 0 and r["v2"] > thr2], key=lambda r: -r["v2"])[:8]],
        "synthetic_missed_lowest": [{"file": r["file"], "score": round(r["v2"], 3)} for r in
                                    sorted([r for r in ae if r["y"] == 1 and r["v2"] <= thr2], key=lambda r: r["v2"])[:8]]}
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    with open(out / "scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "file", "label", "codec", "pre", "v1", "v_only", "ad_only", "v2"])
        for r in rows:
            w.writerow([r["data"], r["file"], "fake" if r["y"] else "real", r["codec"],
                        *[("" if r[k] is None else round(r[k], 5)) for k in ("pre", "v1", "v_only", "ad_only", "v2")]])
    # export v2 (not installed)
    sc, lr = m2.named_steps["standardscaler"], m2.named_steps["logisticregression"]
    v2dir = Path(a.export_dir)
    v2dir.mkdir(parents=True, exist_ok=True)
    params = {"kind": "logistic_regression_on_aasist_embedding", "base_model_version": res["model_version_base"],
              "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(), "coef": lr.coef_[0].tolist(),
              "intercept": float(lr.intercept_[0]),
              "trained_on": "FSDD/Kokoro train+dev + ASVspoof 2019 LA dev subset (B's bundle), 25 Oct 2026"}
    (v2dir / "head.json").write_text(json.dumps(params), encoding="utf-8")
    hv = hashlib.sha256((v2dir / "head.json").read_bytes()).hexdigest()[:12]
    (v2dir / "head_calibration.json").write_text(json.dumps({
        "threshold": thr2, "polarity": "higher_is_fake", "score_kind": "calibrated",
        "model_version": f"{res['model_version_base']}+head@{hv}", "target_false_alarm": FAR,
        "calibrated_on": "5-fold grouped cross-validation on the head_v2 training data (out-of-fold scores)"},
        indent=1), encoding="utf-8")
    # table
    lines = ["| Test set | Model | n (real/fake) | AUC | EER | genuine flagged [95% CI] | synthetic caught [95% CI] |",
             "|---|---|---|---|---|---|---|"]
    for sname, mm in res["results"].items():
        for mname, d in mm.items():
            for part, b in d.items():
                if b["n"] == 0:
                    continue
                lab = mname if part == "all" else f"{mname} / {part}"
                lines.append(f"| {sname} | {lab} | {b['n_real']}/{b['n_fake']} | {b['auc']} | {b['eer']} | "
                             f"{b['genuine_flagged']} {b['genuine_flagged_wilson95']} | "
                             f"{b['synthetic_caught']} {b['synthetic_caught_wilson95']} |")
    (out / "table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
