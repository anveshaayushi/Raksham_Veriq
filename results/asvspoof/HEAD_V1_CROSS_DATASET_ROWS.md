## ASVspoof 2019 LA runs (generated 2026-10-24 19:23 local; commit uncommitted)

Command: `python -m eval --input data/subsets/eval --labels data/subsets/eval/labels.csv --detector head`

| run | size | AUC | EER | genuine flagged (95% Wilson) | synthetic missed (95% Wilson) | abstained | by |
|---|---|---|---|---|---|---|---|
| head_v1 on ASVspoof eval | n=600 (real 300, fake 300) | AUC 0.457 | EER 0.527 | genuine flagged 0.540 [0.483, 0.596] | synthetic missed 0.507 [0.450, 0.563] | abstained 57 | model aasist-pretrained@51d2d9cf0738+head@2713ba5a2159 |

Breakdown by codec / dataset:

| run | size | AUC | EER | genuine flagged (95% Wilson) | synthetic missed (95% Wilson) | abstained | by |
|---|---|---|---|---|---|---|---|
| head_v1 on ASVspoof eval / codec=clean | n=200 (real 100, fake 100) | AUC 0.507 | EER 0.500 | genuine flagged 0.500 [0.404, 0.596] | synthetic missed 0.500 [0.404, 0.596] | abstained 19 |  |
| head_v1 on ASVspoof eval / codec=mp3 | n=200 (real 100, fake 100) | AUC 0.483 | EER 0.490 | genuine flagged 0.500 [0.404, 0.596] | synthetic missed 0.460 [0.366, 0.557] | abstained 19 |  |
| head_v1 on ASVspoof eval / codec=opus | n=200 (real 100, fake 100) | AUC 0.385 | EER 0.590 | genuine flagged 0.620 [0.522, 0.709] | synthetic missed 0.560 [0.462, 0.653] | abstained 19 |  |

Read this honestly:
- The `dev` run is scored WITHOUT a threshold on purpose (the threshold is fitted from it), so it shows every clip as abstained and has no forced-label rates. Use its AUC/EER only.
- ASVspoof 2019 LA is the data the pretrained AASIST was TRAINED on (its authors used the LA train split). Numbers here are in-distribution and flatter the model. They are not evidence for other fake generators, languages or real-world chats.
- `genuine flagged` and `synthetic missed` use the forced label from the dev-fitted threshold (out/calibration_asvspoof_dev.json). Threshold was fitted on the dev split only; the eval split was never used to fit.
- Audio is ASVspoof-derived: if any clip is shown publicly add the ODC-By notice from DISCLOSURE.md.
