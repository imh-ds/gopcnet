# Stage 5c p-Adjusted Screening Alpha Report (R6)

**Reading: CONFIRMS THE CONFOUND BUT NOT THE MECHANISM: the gap still shrinks with noise multiplier, but MINT's own precision no longer declines with p -- EBICglasso's own ln(p)-driven improvement still outpaces MINT's now-stabilized precision.**

Identical grid to Stage 5b (D-048), one substitution: MINT's screening alpha is `alpha(p)`, a log-linear interpolation of Stage 2's own two calibrated anchor points (`.001` at `p=15`, `.0001` at `p=30`), instead of Stage 5b's fixed `.001`. DPI's own `alpha(N)` (D-012's formula) is unchanged.

## F1 gap by noise multiplier -- this charter vs. D-048's own fixed-alpha numbers

| DGP shape | N | noise multiplier | MINT F1 (alpha(p)) | EBICglasso F1 | gap (alpha(p)) | gap (D-048, fixed alpha) |
|---|---|---|---|---|---|---|
| chain_fork_hub | 500 | 1 | 0.9507 | 0.8560 | 0.0948 | 0.0943 |
| chain_fork_hub | 500 | 2 | 0.9548 | 0.8661 | 0.0888 | 0.0699 |
| chain_fork_hub | 500 | 3 | 0.9584 | 0.8700 | 0.0884 | 0.0573 |
| chain_fork_hub | 1500 | 1 | 0.9639 | 0.8448 | 0.1191 | 0.1231 |
| chain_fork_hub | 1500 | 2 | 0.9658 | 0.8510 | 0.1148 | 0.1088 |
| chain_fork_hub | 1500 | 3 | 0.9705 | 0.8523 | 0.1183 | 0.0937 |
| overlap | 500 | 1 | 0.9194 | 0.8893 | 0.0300 | 0.0327 |
| overlap | 500 | 2 | 0.9309 | 0.8933 | 0.0375 | 0.0236 |
| overlap | 500 | 3 | 0.9368 | 0.8965 | 0.0403 | 0.0128 |
| overlap | 1500 | 1 | 0.9518 | 0.8799 | 0.0719 | 0.0700 |
| overlap | 1500 | 2 | 0.9536 | 0.8852 | 0.0683 | 0.0611 |
| overlap | 1500 | 3 | 0.9489 | 0.8908 | 0.0581 | 0.0456 |

## chain_fork_hub

| N | noise multiplier | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 1 | mint | 0.9118 | 1.0000 | 0.9507 | 0.6750 | 0.0061 | 0 |
| 500 | 1 | ebicglasso | 0.7583 | 1.0000 | 0.8560 | 2.1690 | 1.5103 | 0 |
| 500 | 2 | mint | 0.9186 | 1.0000 | 0.9548 | 0.6120 | 0.0172 | 0 |
| 500 | 2 | ebicglasso | 0.7738 | 1.0000 | 0.8661 | 2.0030 | 3.6383 | 0 |
| 500 | 3 | mint | 0.9249 | 1.0000 | 0.9584 | 0.5610 | 0.0128 | 0 |
| 500 | 3 | ebicglasso | 0.7803 | 1.0000 | 0.8700 | 1.9380 | 2.4582 | 0 |
| 1500 | 1 | mint | 0.9358 | 1.0000 | 0.9639 | 0.4980 | 0.0112 | 0 |
| 1500 | 1 | ebicglasso | 0.7406 | 1.0000 | 0.8448 | 2.3510 | 2.6970 | 0 |
| 1500 | 2 | mint | 0.9385 | 1.0000 | 0.9658 | 0.4650 | 0.0130 | 0 |
| 1500 | 2 | ebicglasso | 0.7500 | 1.0000 | 0.8510 | 2.2420 | 2.8060 | 0 |
| 1500 | 3 | mint | 0.9467 | 1.0000 | 0.9705 | 0.3970 | 0.0149 | 0 |
| 1500 | 3 | ebicglasso | 0.7522 | 1.0000 | 0.8523 | 2.2290 | 2.7080 | 0 |

## overlap

| N | noise multiplier | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 1 | mint | 0.8555 | 1.0000 | 0.9194 | 1.8330 | 0.0102 | 0 |
| 500 | 1 | ebicglasso | 0.8073 | 1.0000 | 0.8893 | 2.6230 | 2.0908 | 0 |
| 500 | 2 | mint | 0.8748 | 1.0000 | 0.9309 | 1.5500 | 0.0064 | 0 |
| 500 | 2 | ebicglasso | 0.8136 | 1.0000 | 0.8933 | 2.5170 | 1.1962 | 0 |
| 500 | 3 | mint | 0.8850 | 1.0000 | 0.9368 | 1.4090 | 0.0093 | 0 |
| 500 | 3 | ebicglasso | 0.8186 | 1.0000 | 0.8965 | 2.4300 | 1.6686 | 0 |
| 1500 | 1 | mint | 0.9137 | 1.0000 | 0.9518 | 1.1040 | 0.0142 | 0 |
| 1500 | 1 | ebicglasso | 0.7916 | 1.0000 | 0.8799 | 2.8610 | 1.5585 | 0 |
| 1500 | 2 | mint | 0.9164 | 1.0000 | 0.9536 | 1.0500 | 0.0182 | 0 |
| 1500 | 2 | ebicglasso | 0.8000 | 1.0000 | 0.8852 | 2.7150 | 2.0182 | 0 |
| 1500 | 3 | mint | 0.9082 | 1.0000 | 0.9489 | 1.1570 | 0.0239 | 0 |
| 1500 | 3 | ebicglasso | 0.8087 | 1.0000 | 0.8908 | 2.5650 | 2.4592 | 0 |

Descriptive result, not a validation gate -- see `docs/stage5c_charter.md`'s own decision structure. See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `gap_by_noise_multiplier_vs_d048.png` for complete evidence.
