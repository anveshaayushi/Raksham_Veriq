# Voice benchmark: trained and tested during the finale (24 Oct 2026, Claude C)

**Question:** how well does VERIQ's voice-note check separate real human speech from synthetic (TTS) speech it has
never heard, after WhatsApp-like compression, using exactly the app's preprocessing?

**Data** (`python -m bench.voice.make_set`, generated 2026-10-24; public / synthetic only):
- Real: Free Spoken Digit Dataset (FSDD, CC BY-SA 4.0), 6 speakers, 40 clips each, 7 spoken digits per clip.
- Synthetic: Kokoro-82M TTS (Apache-2.0, via kokoro-onnx), 24 English voices x 10 clips; 4 Hindi voices x 10 (test only).
- All clips band-limited to 8 kHz, loudness-normalised, Opus 16 kbit/s round trip.
- Splits share no speaker and no voice: train 160 clips (2 speakers + 8 voices), dev 160,
  test 160 English + 40 Hindi synthetic.

**Method** (`python -m bench.voice.train_eval`): Claude B's AASIST loader and the app's exact preprocessing (ffmpeg
decode, quality gate, speech-only VAD, 4 s chunks).
- Baseline: pretrained AASIST score.
- Ours: logistic-regression head trained on AASIST's 160-dim embeddings (train split only).
- Both thresholds fixed on dev (target <= 5% of genuine dev clips flagged). Test run once for these numbers.

**Results on the held-out test split** (bootstrap 95% intervals):

| | Pretrained AASIST | AASIST + our trained head |
|---|---|---|
| AUC | 0.669 | **0.82** |
| Equal error rate | 0.35 | **0.2** |
| Genuine clips flagged | 5.0% [0.012, 0.104] | 18.8% [0.106, 0.276] |
| Synthetic clips caught | 15.0% [0.075, 0.23] | **68.8%** [0.583, 0.789] |
| Hindi synthetic caught (language never trained on) | 7.5% | 77.5% |
| Seconds per clip, CPU (2 cores, Linux sandbox) | 0.551 | 0.551 |

The app's own voice path, run on the same test clips, gives the same counts (55/80 synthetic flagged, 15/80
genuine flagged, 31/40 Hindi flagged).

**Failures and lessons**
- The dev threshold did not transfer: about 19% of genuine test clips are flagged, against the 5% target. One test
  speaker accounts for most of these. With so few speakers, the false-alarm rate is uncertain, so a voice flag only
  asks for review.
- Our first training run used whole clips including silences. Through the app's speech-only path it flagged 71 of 80
  genuine clips: the head had partly learned silence and noise differences between the datasets. We retrained with
  the product's preprocessing; the numbers above are from that run.
- A second Opus compression pass lowers synthetic catch to 50/80 (genuine flagged 12/80).
- Limits: one TTS engine, digit strings, 6 real speakers, no real voice clones, no phone-call audio. These are
  in-domain results, not a benchmark.

**In the app:** `app/adapters/voice_head.py` loads `head.json` + `head_calibration.json` (model version
`aasist-pretrained@51d2d9cf0738+head@2713ba5a2159`) into Claude B's voice service. Off by default since 25 Oct (cross-dataset test: AUC 0.457 on ASVspoof LA eval); turn it on with `VERIQ_VOICE_HEAD=1`.
