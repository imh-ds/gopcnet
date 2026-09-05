# Stage 5a Comparator Benchmark Report -- MINT vs. EBICglasso (R6)

Acceptable-recovery threshold fixed before results: mean validation F1 >= `0.90`, held at every larger tested N (a monotone floor, not an isolated crossing). MINT uses D-012's general `alpha(N)` formula uniformly across all five shapes (see `stage5a.py`'s own module docstring for why overlap's specialized formula was not reproduced here). EBICglasso uses `gamma=0.5` throughout, `qgraph`'s own package default.

## Per-shape verdict

| DGP shape | MINT floor N | EBICglasso floor N | Verdict |
|---|---|---|---|
| chain_fork_hub | 400 | none | MINT reaches acceptable recovery; EBICglasso does not on the tested grid |
| overlap | 400 | none | MINT reaches acceptable recovery; EBICglasso does not on the tested grid |
| triangle_balanced | 400 | 400 | no material difference (both floor at N=400) |
| triangle_moderate | 400 | 400 | no material difference (both floor at N=400) |
| triangle_strong | 400 | 400 | no material difference (both floor at N=400) |

## chain_fork_hub

| N | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|
| 400 | mint | 0.9179 | 1.0000 | 0.9541 | 0.6280 | 0.0105 | 0 |
| 400 | ebicglasso | 0.7618 | 1.0000 | 0.8583 | 2.1290 | 2.5501 | 0 |
| 500 | mint | 0.9125 | 1.0000 | 0.9510 | 0.6730 | 0.0109 | 0 |
| 500 | ebicglasso | 0.7538 | 1.0000 | 0.8527 | 2.2350 | 2.6568 | 0 |
| 600 | mint | 0.9166 | 1.0000 | 0.9533 | 0.6410 | 0.0066 | 0 |
| 600 | ebicglasso | 0.7504 | 1.0000 | 0.8509 | 2.2570 | 1.6455 | 0 |
| 750 | mint | 0.9228 | 1.0000 | 0.9568 | 0.5940 | 0.0110 | 0 |
| 750 | ebicglasso | 0.7449 | 1.0000 | 0.8477 | 2.3000 | 2.6783 | 0 |
| 1000 | mint | 0.9267 | 1.0000 | 0.9589 | 0.5660 | 0.0043 | 0 |
| 1000 | ebicglasso | 0.7412 | 1.0000 | 0.8452 | 2.3440 | 1.0637 | 0 |
| 1500 | mint | 0.9363 | 1.0000 | 0.9642 | 0.4940 | 0.0114 | 0 |
| 1500 | ebicglasso | 0.7323 | 1.0000 | 0.8394 | 2.4460 | 2.7841 | 0 |
| 1750 | mint | 0.9391 | 1.0000 | 0.9658 | 0.4720 | 0.0116 | 0 |
| 1750 | ebicglasso | 0.7314 | 1.0000 | 0.8389 | 2.4480 | 2.6967 | 0 |

## overlap

| N | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|
| 400 | mint | 0.8792 | 1.0000 | 0.9332 | 1.5030 | 0.0055 | 0 |
| 400 | ebicglasso | 0.8066 | 1.0000 | 0.8892 | 2.6130 | 1.2788 | 0 |
| 500 | mint | 0.8577 | 1.0000 | 0.9208 | 1.7930 | 0.0072 | 0 |
| 500 | ebicglasso | 0.8019 | 1.0000 | 0.8861 | 2.7070 | 1.5099 | 0 |
| 600 | mint | 0.8478 | 1.0000 | 0.9148 | 1.9430 | 0.0062 | 0 |
| 600 | ebicglasso | 0.8010 | 1.0000 | 0.8856 | 2.7160 | 1.2039 | 0 |
| 750 | mint | 0.8398 | 1.0000 | 0.9101 | 2.0600 | 0.0070 | 0 |
| 750 | ebicglasso | 0.8020 | 1.0000 | 0.8863 | 2.6950 | 1.1099 | 0 |
| 1000 | mint | 0.8611 | 1.0000 | 0.9215 | 1.8130 | 0.0121 | 0 |
| 1000 | ebicglasso | 0.7922 | 1.0000 | 0.8805 | 2.8380 | 1.6530 | 0 |
| 1500 | mint | 0.9153 | 1.0000 | 0.9528 | 1.0780 | 0.0143 | 0 |
| 1500 | ebicglasso | 0.7893 | 1.0000 | 0.8786 | 2.8900 | 1.5621 | 0 |
| 1750 | mint | 0.9265 | 1.0000 | 0.9588 | 0.9520 | 0.0145 | 0 |
| 1750 | ebicglasso | 0.7942 | 1.0000 | 0.8815 | 2.8190 | 1.4829 | 0 |

## triangle_balanced

| N | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|
| 400 | mint | 1.0000 | 0.9997 | 0.9998 | 0.0010 | 0.0013 | 0 |
| 400 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0797 | 0 |
| 500 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0017 | 0 |
| 500 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.1250 | 0 |
| 600 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0012 | 0 |
| 600 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0706 | 0 |
| 750 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0021 | 0 |
| 750 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.1392 | 0 |
| 1000 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0019 | 0 |
| 1000 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.1030 | 0 |
| 1500 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0021 | 0 |
| 1500 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0979 | 0 |
| 1750 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0024 | 0 |
| 1750 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.1165 | 0 |

## triangle_moderate

| N | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|
| 400 | mint | 1.0000 | 0.9470 | 0.9682 | 0.1590 | 0.0017 | 0 |
| 400 | ebicglasso | 1.0000 | 0.9847 | 0.9908 | 0.0460 | 0.2391 | 0 |
| 500 | mint | 1.0000 | 0.9697 | 0.9818 | 0.0910 | 0.0021 | 0 |
| 500 | ebicglasso | 1.0000 | 0.9937 | 0.9962 | 0.0190 | 0.3345 | 0 |
| 600 | mint | 1.0000 | 0.9747 | 0.9848 | 0.0760 | 0.0021 | 0 |
| 600 | ebicglasso | 1.0000 | 0.9953 | 0.9972 | 0.0140 | 0.3220 | 0 |
| 750 | mint | 1.0000 | 0.9883 | 0.9930 | 0.0350 | 0.0019 | 0 |
| 750 | ebicglasso | 1.0000 | 0.9983 | 0.9990 | 0.0050 | 0.2325 | 0 |
| 1000 | mint | 1.0000 | 0.9950 | 0.9970 | 0.0150 | 0.0022 | 0 |
| 1000 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.3007 | 0 |
| 1500 | mint | 1.0000 | 0.9993 | 0.9996 | 0.0020 | 0.0017 | 0 |
| 1500 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.1649 | 0 |
| 1750 | mint | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0024 | 0 |
| 1750 | ebicglasso | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.2755 | 0 |

## triangle_strong

| N | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|
| 400 | mint | 1.0000 | 0.8683 | 0.9208 | 0.3950 | 0.0018 | 0 |
| 400 | ebicglasso | 1.0000 | 0.9530 | 0.9718 | 0.1410 | 0.4909 | 0 |
| 500 | mint | 1.0000 | 0.8880 | 0.9328 | 0.3360 | 0.0012 | 0 |
| 500 | ebicglasso | 1.0000 | 0.9683 | 0.9810 | 0.0950 | 0.2258 | 0 |
| 600 | mint | 1.0000 | 0.9040 | 0.9424 | 0.2880 | 0.0020 | 0 |
| 600 | ebicglasso | 1.0000 | 0.9760 | 0.9856 | 0.0720 | 0.4893 | 0 |
| 750 | mint | 1.0000 | 0.9303 | 0.9582 | 0.2090 | 0.0022 | 0 |
| 750 | ebicglasso | 1.0000 | 0.9873 | 0.9924 | 0.0380 | 0.5179 | 0 |
| 1000 | mint | 1.0000 | 0.9523 | 0.9714 | 0.1430 | 0.0022 | 0 |
| 1000 | ebicglasso | 1.0000 | 0.9953 | 0.9972 | 0.0140 | 0.5044 | 0 |
| 1500 | mint | 1.0000 | 0.9770 | 0.9862 | 0.0690 | 0.0023 | 0 |
| 1500 | ebicglasso | 1.0000 | 0.9993 | 0.9996 | 0.0020 | 0.5156 | 0 |
| 1750 | mint | 1.0000 | 0.9857 | 0.9914 | 0.0430 | 0.0023 | 0 |
| 1750 | ebicglasso | 1.0000 | 0.9987 | 0.9992 | 0.0040 | 0.5104 | 0 |

No claim of superiority is made or implied by this table -- per `docs/stage5a_charter.md`'s own non-goals, a mixed picture is a complete answer. See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `f1_by_n_by_shape.png` for complete evidence.
