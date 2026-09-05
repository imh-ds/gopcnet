# Stage 5e PC-Algorithm Skeleton Comparison Report (R6)

**Recall check: Recall drops below 1.0 for PC in 16 cell(s), worst: triangle_strong N=400 recall=0.7203 -- unlike every prior R6 charter, PC misses real edges here, not just retaining false ones; this is new information for the arc.**

PC uses `alpha=0.01`, fixed (`pcalg`'s own canonical-tutorial convention), skeleton phase only -- no orientation phase implemented at all (see `docs/stage5e_charter.md`). PC's data is drawn identically to D-047's own (same `master_seed`, same condition-seed derivation) -- MINT and EBICglasso columns below are D-047's own published numbers, not re-run.

'Comparable to or better' means PC's mean validation F1 is within `0.01` of, or exceeds, the comparator's own F1 at that `N`; a shape verdict requires this holding at a majority (`>= 4` of `7`) of tested `N`, not necessarily every one -- both fixed before this run, per this module's own docstring.

## Per-shape verdict

| DGP shape | matches MINT (N of 7) | matches EBICglasso (N of 7) | Verdict |
|---|---|---|---|
| chain_fork_hub | 7/7 | 7/7 | PC comparable to or better than MINT at a majority of tested N (7/7) |
| overlap | 7/7 | 7/7 | PC comparable to or better than MINT at a majority of tested N (7/7) |
| triangle_balanced | 7/7 | 7/7 | PC comparable to or better than MINT at a majority of tested N (7/7) |
| triangle_moderate | 2/7 | 2/7 | PC trails both MINT and EBICglasso at a majority of tested N (2/7 vs. MINT, 2/7 vs. EBICglasso) |
| triangle_strong | 0/7 | 0/7 | PC trails both MINT and EBICglasso at a majority of tested N (0/7 vs. MINT, 0/7 vs. EBICglasso) |

## chain_fork_hub

| N | PC F1 | PC recall | MINT F1 (D-047) | EBICglasso F1 (D-047) | matches MINT | matches EBICglasso |
|---|---|---|---|---|---|---|
| 400 | 0.9699 | 1.0000 | 0.9541 | 0.8583 | True | True |
| 500 | 0.9726 | 1.0000 | 0.9510 | 0.8527 | True | True |
| 600 | 0.9709 | 1.0000 | 0.9533 | 0.8509 | True | True |
| 750 | 0.9728 | 1.0000 | 0.9568 | 0.8477 | True | True |
| 1000 | 0.9718 | 1.0000 | 0.9589 | 0.8452 | True | True |
| 1500 | 0.9698 | 1.0000 | 0.9642 | 0.8394 | True | True |
| 1750 | 0.9718 | 1.0000 | 0.9658 | 0.8389 | True | True |

## overlap

| N | PC F1 | PC recall | MINT F1 (D-047) | EBICglasso F1 (D-047) | matches MINT | matches EBICglasso |
|---|---|---|---|---|---|---|
| 400 | 0.9854 | 0.9967 | 0.9332 | 0.8892 | True | True |
| 500 | 0.9850 | 0.9995 | 0.9208 | 0.8861 | True | True |
| 600 | 0.9881 | 0.9998 | 0.9148 | 0.8856 | True | True |
| 750 | 0.9866 | 1.0000 | 0.9101 | 0.8863 | True | True |
| 1000 | 0.9855 | 1.0000 | 0.9215 | 0.8805 | True | True |
| 1500 | 0.9871 | 1.0000 | 0.9528 | 0.8786 | True | True |
| 1750 | 0.9862 | 1.0000 | 0.9588 | 0.8815 | True | True |

## triangle_balanced

| N | PC F1 | PC recall | MINT F1 (D-047) | EBICglasso F1 (D-047) | matches MINT | matches EBICglasso |
|---|---|---|---|---|---|---|
| 400 | 0.9976 | 0.9960 | 0.9998 | 1.0000 | True | True |
| 500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |
| 600 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |
| 750 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |
| 1000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |
| 1500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |
| 1750 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | True | True |

## triangle_moderate

| N | PC F1 | PC recall | MINT F1 (D-047) | EBICglasso F1 (D-047) | matches MINT | matches EBICglasso |
|---|---|---|---|---|---|---|
| 400 | 0.8890 | 0.8150 | 0.9682 | 0.9908 | False | False |
| 500 | 0.9112 | 0.8520 | 0.9818 | 0.9962 | False | False |
| 600 | 0.9278 | 0.8797 | 0.9848 | 0.9972 | False | False |
| 750 | 0.9534 | 0.9223 | 0.9930 | 0.9990 | False | False |
| 1000 | 0.9790 | 0.9650 | 0.9970 | 1.0000 | False | False |
| 1500 | 0.9974 | 0.9957 | 0.9996 | 1.0000 | True | True |
| 1750 | 0.9986 | 0.9977 | 1.0000 | 1.0000 | True | True |

## triangle_strong

| N | PC F1 | PC recall | MINT F1 (D-047) | EBICglasso F1 (D-047) | matches MINT | matches EBICglasso |
|---|---|---|---|---|---|---|
| 400 | 0.8318 | 0.7203 | 0.9208 | 0.9718 | False | False |
| 500 | 0.8410 | 0.7350 | 0.9328 | 0.9810 | False | False |
| 600 | 0.8500 | 0.7500 | 0.9424 | 0.9856 | False | False |
| 750 | 0.8756 | 0.7927 | 0.9582 | 0.9924 | False | False |
| 1000 | 0.8988 | 0.8313 | 0.9714 | 0.9972 | False | False |
| 1500 | 0.9390 | 0.8983 | 0.9862 | 0.9996 | False | False |
| 1750 | 0.9538 | 0.9230 | 0.9914 | 0.9992 | False | False |

### chain_fork_hub -- PC raw metrics

| N | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|
| 400 | 0.9452 | 1.0000 | 0.9699 | 0.4030 | 0.0218 | 0 |
| 500 | 0.9498 | 1.0000 | 0.9726 | 0.3640 | 0.0205 | 0 |
| 600 | 0.9468 | 1.0000 | 0.9709 | 0.3860 | 0.0366 | 0 |
| 750 | 0.9503 | 1.0000 | 0.9728 | 0.3620 | 0.0368 | 0 |
| 1000 | 0.9486 | 1.0000 | 0.9718 | 0.3770 | 0.0188 | 0 |
| 1500 | 0.9450 | 1.0000 | 0.9698 | 0.4020 | 0.0193 | 0 |
| 1750 | 0.9486 | 1.0000 | 0.9718 | 0.3780 | 0.0205 | 0 |

### overlap -- PC raw metrics

| N | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|
| 400 | 0.9755 | 0.9967 | 0.9854 | 0.3070 | 0.0529 | 0 |
| 500 | 0.9720 | 0.9995 | 0.9850 | 0.3190 | 0.0548 | 0 |
| 600 | 0.9776 | 0.9998 | 0.9881 | 0.2530 | 0.0273 | 0 |
| 750 | 0.9747 | 1.0000 | 0.9866 | 0.2860 | 0.0453 | 0 |
| 1000 | 0.9726 | 1.0000 | 0.9855 | 0.3080 | 0.0476 | 0 |
| 1500 | 0.9756 | 1.0000 | 0.9871 | 0.2730 | 0.0675 | 0 |
| 1750 | 0.9740 | 1.0000 | 0.9862 | 0.2950 | 0.0377 | 0 |

### triangle_balanced -- PC raw metrics

| N | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|
| 400 | 1.0000 | 0.9960 | 0.9976 | 0.0120 | 0.0038 | 0 |
| 500 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0038 | 0 |
| 600 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0019 | 0 |
| 750 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0041 | 0 |
| 1000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0028 | 0 |
| 1500 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0017 | 0 |
| 1750 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0046 | 0 |

### triangle_moderate -- PC raw metrics

| N | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|
| 400 | 1.0000 | 0.8150 | 0.8890 | 0.5550 | 0.0037 | 0 |
| 500 | 1.0000 | 0.8520 | 0.9112 | 0.4440 | 0.0037 | 0 |
| 600 | 1.0000 | 0.8797 | 0.9278 | 0.3610 | 0.0038 | 0 |
| 750 | 1.0000 | 0.9223 | 0.9534 | 0.2330 | 0.0039 | 0 |
| 1000 | 1.0000 | 0.9650 | 0.9790 | 0.1050 | 0.0041 | 0 |
| 1500 | 1.0000 | 0.9957 | 0.9974 | 0.0130 | 0.0035 | 0 |
| 1750 | 1.0000 | 0.9977 | 0.9986 | 0.0070 | 0.0041 | 0 |

### triangle_strong -- PC raw metrics

| N | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|
| 400 | 1.0000 | 0.7203 | 0.8318 | 0.8390 | 0.0021 | 0 |
| 500 | 1.0000 | 0.7350 | 0.8410 | 0.7950 | 0.0036 | 0 |
| 600 | 1.0000 | 0.7500 | 0.8500 | 0.7500 | 0.0022 | 0 |
| 750 | 1.0000 | 0.7927 | 0.8756 | 0.6220 | 0.0038 | 0 |
| 1000 | 1.0000 | 0.8313 | 0.8988 | 0.5060 | 0.0039 | 0 |
| 1500 | 1.0000 | 0.8983 | 0.9390 | 0.3050 | 0.0042 | 0 |
| 1750 | 1.0000 | 0.9230 | 0.9538 | 0.2310 | 0.0044 | 0 |

Descriptive result, not a validation gate; skeleton recovery only, no causal-direction claim of any kind -- see `docs/stage5e_charter.md`'s own decision structure and non-goals. See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `pc_vs_d047_f1.png` for complete evidence.
