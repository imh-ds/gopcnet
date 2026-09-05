# Stage 5d Signal-Strength Sweep Report (R6)

**Recall check: Recall stayed at 1.0 for both methods in every cell -- the entire measured gap remains a precision (false-edge) question, as in every prior R6 charter.**

No confirm/refute branch (exploratory axis, per `docs/stage5d_charter.md`'s own "no strong directional prediction" section) -- instead, the F1-gap trend is classified per (dgp, N) series across ascending strength.

## F1-gap trend by (dgp, N)

| DGP shape | N | trend |
|---|---|---|
| chain_fork_hub | 500 | increasing |
| chain_fork_hub | 1500 | increasing |
| overlap | 500 | increasing |
| overlap | 1500 | increasing |

## F1 gap by strength

| DGP shape | N | strength | MINT F1 | MINT recall | EBICglasso F1 | EBICglasso recall | gap |
|---|---|---|---|---|---|---|---|
| chain_fork_hub | 500 | 0.3 | 0.9764 | 1.0000 | 0.9327 | 1.0000 | 0.0437 |
| chain_fork_hub | 500 | 0.5 | 0.9518 | 1.0000 | 0.8561 | 1.0000 | 0.0957 |
| chain_fork_hub | 500 | 0.7 | 0.9489 | 1.0000 | 0.6835 | 1.0000 | 0.2654 |
| chain_fork_hub | 1500 | 0.3 | 0.9790 | 1.0000 | 0.9420 | 1.0000 | 0.0370 |
| chain_fork_hub | 1500 | 0.5 | 0.9616 | 1.0000 | 0.8358 | 1.0000 | 0.1258 |
| chain_fork_hub | 1500 | 0.7 | 0.9627 | 1.0000 | 0.6715 | 1.0000 | 0.2913 |
| overlap | 500 | 0.3 | 0.9295 | 0.9999 | 0.9248 | 1.0000 | 0.0048 |
| overlap | 500 | 0.5 | 0.9196 | 1.0000 | 0.8883 | 1.0000 | 0.0313 |
| overlap | 500 | 0.7 | 0.9196 | 1.0000 | 0.8073 | 1.0000 | 0.1123 |
| overlap | 1500 | 0.3 | 0.9573 | 1.0000 | 0.9240 | 1.0000 | 0.0333 |
| overlap | 1500 | 0.5 | 0.9476 | 1.0000 | 0.8757 | 1.0000 | 0.0719 |
| overlap | 1500 | 0.7 | 0.9522 | 1.0000 | 0.7898 | 1.0000 | 0.1624 |

## chain_fork_hub

| N | strength | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 0.3 | mint | 0.9567 | 1.0000 | 0.9764 | 0.3130 | 0.0039 | 0 |
| 500 | 0.3 | ebicglasso | 0.8816 | 1.0000 | 0.9327 | 0.9450 | 1.0331 | 0 |
| 500 | 0.5 | mint | 0.9140 | 1.0000 | 0.9518 | 0.6640 | 0.0061 | 0 |
| 500 | 0.5 | ebicglasso | 0.7584 | 1.0000 | 0.8561 | 2.1700 | 1.5026 | 0 |
| 500 | 0.7 | mint | 0.9092 | 1.0000 | 0.9489 | 0.7080 | 0.0106 | 0 |
| 500 | 0.7 | ebicglasso | 0.5255 | 1.0000 | 0.6835 | 5.8490 | 3.0192 | 0 |
| 1500 | 0.3 | mint | 0.9623 | 1.0000 | 0.9790 | 0.2850 | 0.0072 | 0 |
| 1500 | 0.3 | ebicglasso | 0.8974 | 1.0000 | 0.9420 | 0.8050 | 1.2579 | 0 |
| 1500 | 0.5 | mint | 0.9319 | 1.0000 | 0.9616 | 0.5310 | 0.0098 | 0 |
| 1500 | 0.5 | ebicglasso | 0.7279 | 1.0000 | 0.8358 | 2.5290 | 2.1763 | 0 |
| 1500 | 0.7 | mint | 0.9336 | 1.0000 | 0.9627 | 0.5140 | 0.0086 | 0 |
| 1500 | 0.7 | ebicglasso | 0.5120 | 1.0000 | 0.6715 | 6.1850 | 2.0647 | 0 |

## overlap

| N | strength | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 500 | 0.3 | mint | 0.8726 | 0.9999 | 0.9295 | 1.5810 | 0.0078 | 0 |
| 500 | 0.3 | ebicglasso | 0.8657 | 1.0000 | 0.9248 | 1.7220 | 1.6483 | 0 |
| 500 | 0.5 | mint | 0.8560 | 1.0000 | 0.9196 | 1.8290 | 0.0097 | 0 |
| 500 | 0.5 | ebicglasso | 0.8049 | 1.0000 | 0.8883 | 2.6380 | 1.9829 | 0 |
| 500 | 0.7 | mint | 0.8555 | 1.0000 | 0.9196 | 1.8210 | 0.0101 | 0 |
| 500 | 0.7 | ebicglasso | 0.6826 | 1.0000 | 0.8073 | 4.9670 | 2.2595 | 0 |
| 1500 | 0.3 | mint | 0.9241 | 1.0000 | 0.9573 | 0.9840 | 0.0100 | 0 |
| 1500 | 0.3 | ebicglasso | 0.8639 | 1.0000 | 0.9240 | 1.7290 | 0.9218 | 0 |
| 1500 | 0.5 | mint | 0.9072 | 1.0000 | 0.9476 | 1.2180 | 0.0068 | 0 |
| 1500 | 0.5 | ebicglasso | 0.7846 | 1.0000 | 0.8757 | 2.9610 | 0.7106 | 0 |
| 1500 | 0.7 | mint | 0.9147 | 1.0000 | 0.9522 | 1.1000 | 0.0086 | 0 |
| 1500 | 0.7 | ebicglasso | 0.6580 | 1.0000 | 0.7898 | 5.5230 | 1.1213 | 0 |

Descriptive result, not a validation gate -- see `docs/stage5d_charter.md`'s own decision structure. See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `gap_by_strength.png` for complete evidence.
