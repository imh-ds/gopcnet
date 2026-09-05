# Stage 5b Noise-Column-Count Stress Test Report (R6)

**Reading: COMPLICATES the mechanism: the F1 gap decreases with noise multiplier at at least one (dgp, N) condition beyond sampling tolerance -- D-047's noise-column-count explanation needs its own diagnosis before further R6 charters build on it.**

Extends D-047's own two composed, noisy p=15 networks by appending extra independent standard-normal noise columns (multiplier x each shape's own native noise-column count) while holding strength (`.5`), MINT's alpha(N), and EBICglasso's gamma unchanged from `docs/stage5a_charter.md`.

## F1 gap by noise multiplier

| DGP shape | N | noise multiplier | MINT F1 | EBICglasso F1 | gap (MINT - EBICglasso) |
|---|---|---|---|---|---|
| chain_fork_hub | 500 | 1 | 0.9513 | 0.8569 | 0.0943 |
| chain_fork_hub | 500 | 2 | 0.9406 | 0.8707 | 0.0699 |
| chain_fork_hub | 500 | 3 | 0.9255 | 0.8682 | 0.0573 |
| chain_fork_hub | 1500 | 1 | 0.9666 | 0.8435 | 0.1231 |
| chain_fork_hub | 1500 | 2 | 0.9543 | 0.8455 | 0.1088 |
| chain_fork_hub | 1500 | 3 | 0.9430 | 0.8493 | 0.0937 |
| overlap | 500 | 1 | 0.9192 | 0.8865 | 0.0327 |
| overlap | 500 | 2 | 0.9162 | 0.8926 | 0.0236 |
| overlap | 500 | 3 | 0.9139 | 0.9010 | 0.0128 |
| overlap | 1500 | 1 | 0.9503 | 0.8803 | 0.0700 |
| overlap | 1500 | 2 | 0.9456 | 0.8845 | 0.0611 |
| overlap | 1500 | 3 | 0.9389 | 0.8933 | 0.0456 |

## chain_fork_hub

| N | noise multiplier | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 1 | mint | 0.9132 | 1.0000 | 0.9513 | 0.6710 | 0.0105 | 0 |
| 500 | 1 | ebicglasso | 0.7600 | 1.0000 | 0.8569 | 2.1590 | 2.6707 | 0 |
| 500 | 2 | mint | 0.8950 | 1.0000 | 0.9406 | 0.8270 | 0.0080 | 0 |
| 500 | 2 | ebicglasso | 0.7808 | 1.0000 | 0.8707 | 1.9170 | 1.6377 | 0 |
| 500 | 3 | mint | 0.8701 | 1.0000 | 0.9255 | 1.0590 | 0.0184 | 0 |
| 500 | 3 | ebicglasso | 0.7763 | 1.0000 | 0.8682 | 1.9520 | 3.5994 | 0 |
| 1500 | 1 | mint | 0.9405 | 1.0000 | 0.9666 | 0.4600 | 0.0112 | 0 |
| 1500 | 1 | ebicglasso | 0.7385 | 1.0000 | 0.8435 | 2.3730 | 2.7034 | 0 |
| 1500 | 2 | mint | 0.9193 | 1.0000 | 0.9543 | 0.6380 | 0.0087 | 0 |
| 1500 | 2 | ebicglasso | 0.7421 | 1.0000 | 0.8455 | 2.3500 | 1.7735 | 0 |
| 1500 | 3 | mint | 0.9000 | 1.0000 | 0.9430 | 0.8010 | 0.0212 | 0 |
| 1500 | 3 | ebicglasso | 0.7478 | 1.0000 | 0.8493 | 2.2770 | 3.7366 | 0 |

## overlap

| N | noise multiplier | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 1 | mint | 0.8549 | 1.0000 | 0.9192 | 1.8340 | 0.0056 | 0 |
| 500 | 1 | ebicglasso | 0.8024 | 1.0000 | 0.8865 | 2.6880 | 1.1964 | 0 |
| 500 | 2 | mint | 0.8501 | 1.0000 | 0.9162 | 1.9090 | 0.0078 | 0 |
| 500 | 2 | ebicglasso | 0.8121 | 1.0000 | 0.8926 | 2.5250 | 1.5205 | 0 |
| 500 | 3 | mint | 0.8466 | 1.0000 | 0.9139 | 1.9770 | 0.0123 | 0 |
| 500 | 3 | ebicglasso | 0.8260 | 1.0000 | 0.9010 | 2.3150 | 2.3091 | 0 |
| 1500 | 1 | mint | 0.9111 | 1.0000 | 0.9503 | 1.1390 | 0.0086 | 0 |
| 1500 | 1 | ebicglasso | 0.7918 | 1.0000 | 0.8803 | 2.8440 | 0.8890 | 0 |
| 1500 | 2 | mint | 0.9037 | 1.0000 | 0.9456 | 1.2660 | 0.0109 | 0 |
| 1500 | 2 | ebicglasso | 0.7995 | 1.0000 | 0.8845 | 2.7470 | 1.2225 | 0 |
| 1500 | 3 | mint | 0.8924 | 1.0000 | 0.9389 | 1.4320 | 0.0156 | 0 |
| 1500 | 3 | ebicglasso | 0.8131 | 1.0000 | 0.8933 | 2.5060 | 1.7229 | 0 |

Descriptive result, not a validation gate -- see `docs/stage5b_charter.md`'s own decision structure. See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `gap_by_noise_multiplier.png` for complete evidence.
