"""Voice benchmark set, generated during the finale (24 Oct 2026) by Claude C. Synthetic + public data only.

Real ("bonafide"): Free Spoken Digit Dataset (FSDD, CC BY-SA 4.0), 6 English speakers, 8 kHz recordings.
Fake ("spoof"):    Kokoro-82M TTS (Apache-2.0) via kokoro-onnx: 24 English voices; plus 4 Hindi voices (test only).
Each clip: 7 spoken digits. Both classes are band-limited to 8 kHz, resampled to 16 kHz and loudness-normalised,
then sent through a WhatsApp-like Opus round trip (16 kbit/s) so the codec doesn't give the answer away.
Splits share NO speaker and NO voice: train (fit the classifier head), dev (pick the threshold), test (report only).

Usage:  python -m bench.voice.make_set --fsdd <fsdd/recordings> --kokoro <kokoro-v1.0.onnx> --voices <voices-v1.0.bin> --out <dir>
Writes <out>/<split>/<clip>.wav and <out>/labels.csv (file,label,source,split,lang,seconds).
LIMITS: tiny (6 real speakers), digits only, one TTS engine; real speech and TTS differ in more than "fakeness".
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import random
import subprocess
import tempfile

import numpy as np
import soundfile as sf

SEED = 20261024
SPK = ["george", "jackson", "lucas", "nicolas", "theo", "yweweler"]
SPK_SPLIT = {"george": "train", "jackson": "train", "lucas": "dev", "nicolas": "dev", "theo": "test", "yweweler": "test"}
EN_VOICES = ["af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica", "af_kore", "af_nicole", "af_nova",
             "af_river", "af_sarah", "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
             "am_onyx", "am_puck", "bf_alice", "bf_emma", "bf_isabella", "bm_daniel", "bm_george"]
HI_VOICES = ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"]
WORDS = "zero one two three four five six seven eight nine".split()
HI_WORDS = "शून्य एक दो तीन चार पाँच छह सात आठ नौ".split()


def resample(x, a, b):
    import torch
    import torchaudio.functional as AF
    return AF.resample(torch.tensor(x, dtype=torch.float32), a, b).numpy()


def finish(x, sr):
    """band-limit to 8 kHz, back to 16 kHz, normalise, Opus 16 kbit/s round trip."""
    x = resample(resample(x, sr, 8000), 8000, 16000)
    x = (x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.08).clip(-1, 1).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        a, o, b = os.path.join(d, "a.wav"), os.path.join(d, "a.opus"), os.path.join(d, "b.wav")
        sf.write(a, x, 16000)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-c:a", "libopus", "-b:a", "16k", o], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", o, "-ar", "16000", "-ac", "1", b], check=True)
        y, _ = sf.read(b, dtype="float32")
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fsdd", required=True)
    ap.add_argument("--kokoro", required=True)
    ap.add_argument("--voices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-speaker", type=int, default=40)
    ap.add_argument("--per-voice", type=int, default=10)
    a = ap.parse_args()
    rng = random.Random(SEED)
    for s in ("train", "dev", "test"):
        os.makedirs(os.path.join(a.out, s), exist_ok=True)
    rows = []
    by = {}
    for f in glob.glob(os.path.join(a.fsdd, "*.wav")):
        d, s, _ = os.path.basename(f)[:-4].split("_")
        by.setdefault((s, int(d)), []).append(f)
    gap = np.zeros(int(0.12 * 8000), dtype=np.float32)
    for s in SPK:
        split = SPK_SPLIT[s]
        for n in range(a.per_speaker):
            parts = []
            for _ in range(7):
                x, sr = sf.read(rng.choice(by[(s, rng.randint(0, 9))]), dtype="float32")
                parts += [x, gap]
            y = finish(np.concatenate(parts), 8000)
            name = f"real_{s}_{n:02d}.wav"
            sf.write(os.path.join(a.out, split, name), y, 16000)
            rows.append([f"{split}/{name}", "real", s, split, "en", round(len(y) / 16000, 2)])
    from kokoro_onnx import Kokoro
    k = Kokoro(a.kokoro, a.voices)
    for i, v in enumerate(EN_VOICES):
        split = ["train", "dev", "test"][i % 3]
        for n in range(a.per_voice):
            text = ", ".join(rng.choice(WORDS) for _ in range(7))
            x, sr = k.create(text, voice=v, speed=rng.choice([0.9, 1.0, 1.1]), lang="en-gb" if v[0] == "b" else "en-us")
            y = finish(x, sr)
            name = f"fake_{v}_{n:02d}.wav"
            sf.write(os.path.join(a.out, split, name), y, 16000)
            rows.append([f"{split}/{name}", "fake", v, split, "en", round(len(y) / 16000, 2)])
    for v in HI_VOICES:
        for n in range(a.per_voice):
            text = ", ".join(rng.choice(HI_WORDS) for _ in range(7))
            x, sr = k.create(text, voice=v, speed=1.0, lang="hi")
            y = finish(x, sr)
            name = f"fake_{v}_{n:02d}.wav"
            sf.write(os.path.join(a.out, "test", name), y, 16000)
            rows.append([f"test/{name}", "fake", v, "test", "hi", round(len(y) / 16000, 2)])
    with open(os.path.join(a.out, "labels.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "label", "source", "split", "lang", "seconds"])
        w.writerows(rows)
    print(len(rows), "clips")


if __name__ == "__main__":
    main()
