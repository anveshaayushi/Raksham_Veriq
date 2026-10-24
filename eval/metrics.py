"""Pure-numpy metrics. Convention: POSITIVE = fake. `fake_score`: higher = more likely fake.

For a higher_is_real detector pass fake_score = -score.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def auc(fake_scores_fake: Sequence[float], fake_scores_real: Sequence[float]) -> Optional[float]:
    """Probability a random fake outranks a random real (ties count 0.5). None if a class is empty."""
    f = np.asarray(fake_scores_fake, dtype=float)
    r = np.asarray(fake_scores_real, dtype=float)
    if f.size == 0 or r.size == 0:
        return None
    gt = (f[:, None] > r[None, :]).sum()
    eq = (f[:, None] == r[None, :]).sum()
    return float((gt + 0.5 * eq) / (f.size * r.size))


def eer(fake_scores_fake: Sequence[float], fake_scores_real: Sequence[float]) -> Optional[float]:
    """Equal error rate (0 = perfect, 0.5 = guessing). None if a class is empty."""
    f = np.asarray(fake_scores_fake, dtype=float)
    r = np.asarray(fake_scores_real, dtype=float)
    if f.size == 0 or r.size == 0:
        return None
    best, best_gap = 0.5, 9.0
    for t in np.unique(np.concatenate([f, r])):
        miss = float(np.mean(f < t))  # fakes not flagged (flag if score >= t)
        fa = float(np.mean(r >= t))  # reals flagged
        gap = abs(miss - fa)
        if gap < best_gap:
            best_gap, best = gap, (miss + fa) / 2
    return float(best)


def threshold_for_far(real_scores_real_high: Sequence[float], far: float) -> float:
    """Threshold t for a higher_is_real score: flag if score < t.

    Chosen so at most `far` of the given GENUINE scores are flagged. Fit on DEV data only.
    """
    r = np.asarray(real_scores_real_high, dtype=float)
    if r.size == 0:
        raise ValueError("need at least one genuine score")
    return float(np.quantile(r, far, method="lower"))


def rates(labels: Sequence[str], preds: Sequence[Optional[str]]) -> dict:
    """False-alarm and miss rate from forced labels. labels/preds in {'real','fake'}; preds may be None (skipped)."""
    real = [(l, p) for l, p in zip(labels, preds) if l == "real" and p is not None]
    fake = [(l, p) for l, p in zip(labels, preds) if l == "fake" and p is not None]
    return {
        "false_alarm": (sum(p == "fake" for _, p in real) / len(real)) if real else None,
        "miss": (sum(p == "real" for _, p in fake) / len(fake)) if fake else None,
        "n_real": len(real),
        "n_fake": len(fake),
    }
