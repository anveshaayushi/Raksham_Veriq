## ASVspoof 2019 LA runs (generated 2026-10-25 00:14 local; commit 844fdd0)

Command: `python scripts/b_run_all.py --zip LA.zip --n-dev 60 --n-eval 100 --far 0.05`

| run | size | AUC | EER | genuine flagged (95% Wilson) | synthetic missed (95% Wilson) | abstained | by |
|---|---|---|---|---|---|---|---|
| dev | n=360 (real 180, fake 180) | AUC 0.948 | EER 0.150 | genuine flagged n/a [n/a, n/a] | synthetic missed n/a [n/a, n/a] | abstained 360 | model aasist-pretrained@51d2d9cf0738 |
| eval | n=600 (real 300, fake 300) | AUC 0.766 | EER 0.317 | genuine flagged 0.157 [0.120, 0.202] | synthetic missed 0.563 [0.507, 0.618] | abstained 57 | model aasist-pretrained@51d2d9cf0738 |
| dev_first_1s | n=120 (real 60, fake 60) | AUC 0.752 | EER 0.383 | genuine flagged 0.150 [0.081, 0.261] | synthetic missed 0.533 [0.409, 0.654] | abstained 120 | model aasist-pretrained@51d2d9cf0738 |
| dev_first_2s | n=120 (real 60, fake 60) | AUC 0.704 | EER 0.300 | genuine flagged 0.483 [0.362, 0.607] | synthetic missed 0.200 [0.118, 0.318] | abstained 70 | model aasist-pretrained@51d2d9cf0738 |
| dev_first_4s | n=120 (real 60, fake 60) | AUC 0.945 | EER 0.150 | genuine flagged 0.067 [0.026, 0.159] | synthetic missed 0.233 [0.144, 0.354] | abstained 13 | model aasist-pretrained@51d2d9cf0738 |

Breakdown by codec / dataset:

| run | size | AUC | EER | genuine flagged (95% Wilson) | synthetic missed (95% Wilson) | abstained | by |
|---|---|---|---|---|---|---|---|
| dev / codec=clean | n=120 (real 60, fake 60) | AUC 0.966 | EER 0.117 | genuine flagged n/a [n/a, n/a] | synthetic missed n/a [n/a, n/a] | abstained 120 |  |
| dev / codec=mp3 | n=120 (real 60, fake 60) | AUC 0.949 | EER 0.150 | genuine flagged n/a [n/a, n/a] | synthetic missed n/a [n/a, n/a] | abstained 120 |  |
| dev / codec=opus | n=120 (real 60, fake 60) | AUC 0.931 | EER 0.183 | genuine flagged n/a [n/a, n/a] | synthetic missed n/a [n/a, n/a] | abstained 120 |  |
| eval / codec=clean | n=200 (real 100, fake 100) | AUC 0.817 | EER 0.270 | genuine flagged 0.110 [0.063, 0.186] | synthetic missed 0.570 [0.472, 0.663] | abstained 19 |  |
| eval / codec=mp3 | n=200 (real 100, fake 100) | AUC 0.782 | EER 0.300 | genuine flagged 0.090 [0.048, 0.162] | synthetic missed 0.580 [0.482, 0.672] | abstained 19 |  |
| eval / codec=opus | n=200 (real 100, fake 100) | AUC 0.701 | EER 0.370 | genuine flagged 0.270 [0.193, 0.364] | synthetic missed 0.540 [0.443, 0.634] | abstained 19 |  |

Read this honestly:
- The `dev` run is scored WITHOUT a threshold on purpose (the threshold is fitted from it), so it shows every clip as abstained and has no forced-label rates. Use its AUC/EER only.
- ASVspoof 2019 LA is the data the pretrained AASIST was TRAINED on (its authors used the LA train split). Numbers here are in-distribution and flatter the model. They are not evidence for other fake generators, languages or real-world chats.
- `genuine flagged` and `synthetic missed` use the forced label from the dev-fitted threshold (out/calibration_asvspoof_dev.json). Threshold was fitted on the dev split only; the eval split was never used to fit.
- Audio is ASVspoof-derived: if any clip is shown publicly add the ODC-By notice from DISCLOSURE.md.
