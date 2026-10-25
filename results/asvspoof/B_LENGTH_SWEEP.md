| first N seconds | clips | scored | speech_s (median) | AUC | EER | genuine flagged | synthetic missed | abstained |
|---|---|---|---|---|---|---|---|---|
| 0.1s | 200 | 200 | 0.00 | 0.849 | 0.230 | 0.000 | 0.790 | 200 |
| 0.25s | 200 | 200 | 0.00 | 0.873 | 0.180 | 0.000 | 0.330 | 200 |
| 0.5s | 200 | 200 | 0.00 | 0.873 | 0.180 | 0.000 | 0.310 | 200 |
| 1s | 200 | 200 | 0.21 | 0.799 | 0.190 | 0.160 | 0.330 | 200 |
| 2s | 200 | 200 | 1.02 | 0.552 | 0.480 | 0.570 | 0.390 | 87 |
| 3s | 200 | 200 | 1.53 | 0.727 | 0.340 | 0.220 | 0.530 | 22 |
| 4s | 200 | 200 | 1.62 | 0.817 | 0.240 | 0.120 | 0.550 | 20 |
| 6s | 200 | 200 | 1.64 | 0.817 | 0.270 | 0.110 | 0.580 | 19 |

Read this honestly:
- Same 200 base clips (100 real, 100 fake, ASVspoof 2019 LA eval, clean only) at every length. The model was trained on this dataset.
- Threshold = dev-fitted (not tuned on these clips). If genuine flagged is far above 5%, the threshold does not transfer to that length.
- 'abstained' counts clips the gate refuses (not enough speech). A refusal is the correct answer for a clip with no speech.
- Many LA clips are only a few seconds long, so the longest rows are often the whole clip.
