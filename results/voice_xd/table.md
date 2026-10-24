| Test set | Model | n (real/fake) | AUC | EER | genuine flagged [95% CI] | synthetic caught [95% CI] |
|---|---|---|---|---|---|---|
| AE (ASVspoof eval, unseen attacks + speakers) | pretrained AASIST (threshold: B's ASVspoof dev) | 276/267 | 0.777 | 0.308 | 0.13 [0.096, 0.175] | 0.412 [0.355, 0.472] |
| AE (ASVspoof eval, unseen attacks + speakers) | pretrained AASIST (threshold: B's ASVspoof dev) / clean | 92/89 | 0.826 | 0.237 | 0.087 [0.045, 0.162] | 0.404 [0.309, 0.508] |
| AE (ASVspoof eval, unseen attacks + speakers) | pretrained AASIST (threshold: B's ASVspoof dev) / mp3 | 92/89 | 0.798 | 0.282 | 0.065 [0.03, 0.135] | 0.393 [0.298, 0.497] |
| AE (ASVspoof eval, unseen attacks + speakers) | pretrained AASIST (threshold: B's ASVspoof dev) / opus | 92/89 | 0.709 | 0.365 | 0.239 [0.164, 0.336] | 0.438 [0.34, 0.542] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v1 as shipped (threshold: FSDD/Kokoro dev) | 276/267 | 0.474 | 0.519 | 0.533 [0.474, 0.591] | 0.509 [0.45, 0.569] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v1 as shipped (threshold: FSDD/Kokoro dev) / clean | 92/89 | 0.53 | 0.481 | 0.489 [0.389, 0.59] | 0.517 [0.415, 0.618] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v1 as shipped (threshold: FSDD/Kokoro dev) / mp3 | 92/89 | 0.492 | 0.481 | 0.489 [0.389, 0.59] | 0.551 [0.447, 0.65] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v1 as shipped (threshold: FSDD/Kokoro dev) / opus | 92/89 | 0.402 | 0.586 | 0.62 [0.517, 0.712] | 0.461 [0.361, 0.564] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on V only (threshold: grouped CV on V) | 276/267 | 0.583 | 0.438 | 0.25 [0.203, 0.304] | 0.371 [0.315, 0.43] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on V only (threshold: grouped CV on V) / clean | 92/89 | 0.665 | 0.392 | 0.152 [0.093, 0.239] | 0.36 [0.268, 0.463] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on V only (threshold: grouped CV on V) / mp3 | 92/89 | 0.594 | 0.431 | 0.25 [0.173, 0.347] | 0.393 [0.298, 0.497] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on V only (threshold: grouped CV on V) / opus | 92/89 | 0.483 | 0.519 | 0.348 [0.258, 0.449] | 0.36 [0.268, 0.463] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on ASVspoof dev only (threshold: grouped CV on AD) | 276/267 | 0.865 | 0.203 | 0.094 [0.065, 0.134] | 0.678 [0.62, 0.731] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on ASVspoof dev only (threshold: grouped CV on AD) / clean | 92/89 | 0.889 | 0.182 | 0.065 [0.03, 0.135] | 0.629 [0.525, 0.722] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on ASVspoof dev only (threshold: grouped CV on AD) / mp3 | 92/89 | 0.881 | 0.188 | 0.054 [0.023, 0.121] | 0.663 [0.56, 0.753] |
| AE (ASVspoof eval, unseen attacks + speakers) | head trained on ASVspoof dev only (threshold: grouped CV on AD) / opus | 92/89 | 0.832 | 0.232 | 0.163 [0.101, 0.252] | 0.742 [0.642, 0.821] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) | 276/267 | 0.832 | 0.239 | 0.051 [0.03, 0.083] | 0.438 [0.38, 0.498] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) / clean | 92/89 | 0.864 | 0.204 | 0.043 [0.017, 0.107] | 0.438 [0.34, 0.542] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) / mp3 | 92/89 | 0.844 | 0.215 | 0.033 [0.011, 0.092] | 0.427 [0.329, 0.531] |
| AE (ASVspoof eval, unseen attacks + speakers) | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) / opus | 92/89 | 0.797 | 0.276 | 0.076 [0.037, 0.149] | 0.449 [0.35, 0.553] |
| V test (FSDD/Kokoro held-out speakers/voices, English) | pretrained AASIST (threshold: B's ASVspoof dev) | 80/80 | 0.669 | 0.35 | 0.188 [0.117, 0.287] | 0.312 [0.222, 0.421] |
| V test (FSDD/Kokoro held-out speakers/voices, English) | head_v1 as shipped (threshold: FSDD/Kokoro dev) | 80/80 | 0.82 | 0.2 | 0.188 [0.117, 0.287] | 0.688 [0.579, 0.778] |
| V test (FSDD/Kokoro held-out speakers/voices, English) | head trained on V only (threshold: grouped CV on V) | 80/80 | 0.85 | 0.212 | 0.037 [0.013, 0.105] | 0.388 [0.288, 0.497] |
| V test (FSDD/Kokoro held-out speakers/voices, English) | head trained on ASVspoof dev only (threshold: grouped CV on AD) | 80/80 | 0.631 | 0.413 | 0.125 [0.069, 0.215] | 0.15 [0.088, 0.244] |
| V test (FSDD/Kokoro held-out speakers/voices, English) | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) | 80/80 | 0.836 | 0.275 | 0.075 [0.035, 0.154] | 0.4 [0.3, 0.51] |
| V test Hindi synthetic only | pretrained AASIST (threshold: B's ASVspoof dev) | 0/40 | None | None | None None | 0.15 [0.071, 0.291] |
| V test Hindi synthetic only | head_v1 as shipped (threshold: FSDD/Kokoro dev) | 0/40 | None | None | None None | 0.775 [0.625, 0.877] |
| V test Hindi synthetic only | head trained on V only (threshold: grouped CV on V) | 0/40 | None | None | None None | 0.625 [0.47, 0.758] |
| V test Hindi synthetic only | head trained on ASVspoof dev only (threshold: grouped CV on AD) | 0/40 | None | None | None None | 0.125 [0.055, 0.261] |
| V test Hindi synthetic only | head_v2 trained on V + ASVspoof dev (threshold: grouped CV) | 0/40 | None | None | None None | 0.8 [0.652, 0.895] |
