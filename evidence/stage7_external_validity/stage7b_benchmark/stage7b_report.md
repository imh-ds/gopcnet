# Stage 7b report: external validity

Charter: `docs/stage7b_charter.md`. Questions use validation replicates; verdict counts use cells with N >= 500 (N = 250 is characterization only).

## Gates

- **G1**: True -- identical fraction 1.0000 over 1200 rows.
- **G2**: True -- 0 of 7500 truths differ across N.
- **G3**: True -- [{"n": 1000, "precision_ours": 0.9316428571428571, "precision_archive": 0.9331607142857143, "precision_z": -0.34956738810102106, "recall_ours": 1.0, "recall_archive": 1.0, "recall_z": 0.0, "rows_with_identical_seed": 500}, {"n": 1500, "precision_ours": 0.946952380952381, "precision_archive": 0.9449464285714285, "precision_z": 0.503953784526809, "recall_ours": 1.0, "recall_archive": 1.0, "recall_z": 0.0, "rows_with_identical_seed": 500}]

## Routing outcome: **C**

## Q2 -- GOPC vs EBICglasso (niche claim)

- **clustered**: PARTIAL (6/9)
- **random_dense**: HOLDS (7/9)
- **random_sparse**: HOLDS (9/9)
- **random_with_isolates**: HOLDS (7/9)
- **small_world**: HOLDS (8/9)

| structure | p | N | precision diff [CI] | F1 diff [CI] | supports |
|---|---|---|---|---|---|
| clustered | 10 | 250 | 0.053 [0.042, 0.065] | 0.027 [0.003, 0.051] | False |
| clustered | 10 | 500 | 0.089 [0.076, 0.102] | -0.009 [-0.025, 0.008] | False |
| clustered | 10 | 1000 | 0.127 [0.115, 0.139] | 0.026 [0.016, 0.037] | True |
| clustered | 10 | 2000 | 0.139 [0.127, 0.151] | 0.057 [0.050, 0.066] | True |
| clustered | 20 | 250 | 0.057 [0.046, 0.068] | 0.035 [0.013, 0.058] | False |
| clustered | 20 | 500 | 0.107 [0.096, 0.117] | -0.015 [-0.025, -0.006] | False |
| clustered | 20 | 1000 | 0.158 [0.148, 0.168] | 0.039 [0.032, 0.046] | True |
| clustered | 20 | 2000 | 0.182 [0.172, 0.193] | 0.082 [0.075, 0.089] | True |
| clustered | 30 | 250 | 0.088 [0.078, 0.098] | -0.022 [-0.037, -0.006] | False |
| clustered | 30 | 500 | 0.143 [0.133, 0.153] | -0.023 [-0.030, -0.015] | False |
| clustered | 30 | 1000 | 0.192 [0.183, 0.202] | 0.052 [0.045, 0.059] | True |
| clustered | 30 | 2000 | 0.227 [0.217, 0.236] | 0.106 [0.099, 0.113] | True |
| random_dense | 10 | 250 | 0.075 [0.062, 0.089] | 0.029 [0.006, 0.052] | True |
| random_dense | 10 | 500 | 0.122 [0.109, 0.135] | -0.011 [-0.024, 0.003] | False |
| random_dense | 10 | 1000 | 0.160 [0.148, 0.172] | 0.042 [0.032, 0.052] | True |
| random_dense | 10 | 2000 | 0.183 [0.171, 0.194] | 0.081 [0.073, 0.089] | True |
| random_dense | 20 | 250 | 0.200 [0.192, 0.208] | -0.043 [-0.049, -0.037] | False |
| random_dense | 20 | 500 | 0.240 [0.234, 0.246] | -0.001 [-0.006, 0.005] | True |
| random_dense | 20 | 1000 | 0.261 [0.255, 0.267] | 0.048 [0.042, 0.054] | True |
| random_dense | 20 | 2000 | 0.281 [0.275, 0.287] | 0.084 [0.078, 0.090] | True |
| random_dense | 30 | 250 | 0.025 [0.008, 0.046] | 0.280 [0.252, 0.306] | False |
| random_dense | 30 | 500 | 0.167 [0.161, 0.173] | -0.028 [-0.034, -0.023] | False |
| random_dense | 30 | 1000 | 0.187 [0.183, 0.192] | -0.000 [-0.005, 0.004] | True |
| random_dense | 30 | 2000 | 0.188 [0.183, 0.194] | 0.020 [0.016, 0.024] | True |
| random_sparse | 10 | 250 | 0.048 [0.035, 0.062] | 0.076 [0.050, 0.104] | False |
| random_sparse | 10 | 500 | 0.078 [0.065, 0.091] | 0.020 [-0.000, 0.042] | True |
| random_sparse | 10 | 1000 | 0.102 [0.089, 0.116] | 0.023 [0.012, 0.034] | True |
| random_sparse | 10 | 2000 | 0.122 [0.108, 0.135] | 0.056 [0.047, 0.064] | True |
| random_sparse | 20 | 250 | 0.109 [0.095, 0.123] | 0.028 [0.011, 0.045] | True |
| random_sparse | 20 | 500 | 0.180 [0.167, 0.192] | 0.022 [0.012, 0.033] | True |
| random_sparse | 20 | 1000 | 0.228 [0.216, 0.241] | 0.085 [0.075, 0.094] | True |
| random_sparse | 20 | 2000 | 0.248 [0.237, 0.260] | 0.126 [0.118, 0.133] | True |
| random_sparse | 30 | 250 | 0.154 [0.143, 0.164] | 0.015 [0.006, 0.025] | True |
| random_sparse | 30 | 500 | 0.254 [0.246, 0.261] | 0.039 [0.034, 0.045] | True |
| random_sparse | 30 | 1000 | 0.300 [0.294, 0.307] | 0.102 [0.097, 0.108] | True |
| random_sparse | 30 | 2000 | 0.333 [0.327, 0.339] | 0.152 [0.147, 0.157] | True |
| random_with_isolates | 10 | 250 | 0.018 [0.000, 0.034] | 0.109 [0.079, 0.139] | False |
| random_with_isolates | 10 | 500 | 0.047 [0.029, 0.064] | 0.077 [0.046, 0.110] | False |
| random_with_isolates | 10 | 1000 | 0.055 [0.043, 0.067] | 0.015 [-0.001, 0.033] | False |
| random_with_isolates | 10 | 2000 | 0.070 [0.056, 0.084] | 0.028 [0.018, 0.037] | True |
| random_with_isolates | 20 | 250 | 0.051 [0.037, 0.064] | 0.069 [0.049, 0.091] | False |
| random_with_isolates | 20 | 500 | 0.102 [0.090, 0.115] | 0.008 [-0.005, 0.023] | True |
| random_with_isolates | 20 | 1000 | 0.148 [0.135, 0.161] | 0.043 [0.034, 0.052] | True |
| random_with_isolates | 20 | 2000 | 0.168 [0.155, 0.180] | 0.080 [0.072, 0.088] | True |
| random_with_isolates | 30 | 250 | 0.129 [0.116, 0.142] | 0.006 [-0.006, 0.019] | True |
| random_with_isolates | 30 | 500 | 0.201 [0.189, 0.213] | 0.028 [0.019, 0.036] | True |
| random_with_isolates | 30 | 1000 | 0.241 [0.230, 0.251] | 0.088 [0.080, 0.096] | True |
| random_with_isolates | 30 | 2000 | 0.278 [0.267, 0.289] | 0.134 [0.127, 0.142] | True |
| small_world | 10 | 250 | 0.114 [0.100, 0.127] | -0.024 [-0.040, -0.005] | False |
| small_world | 10 | 500 | 0.151 [0.140, 0.162] | -0.006 [-0.017, 0.004] | True |
| small_world | 10 | 1000 | 0.193 [0.182, 0.204] | 0.055 [0.047, 0.064] | True |
| small_world | 10 | 2000 | 0.201 [0.191, 0.211] | 0.081 [0.074, 0.089] | True |
| small_world | 20 | 250 | 0.080 [0.070, 0.090] | 0.005 [-0.014, 0.025] | True |
| small_world | 20 | 500 | 0.146 [0.135, 0.156] | -0.004 [-0.012, 0.003] | True |
| small_world | 20 | 1000 | 0.190 [0.180, 0.201] | 0.058 [0.051, 0.065] | True |
| small_world | 20 | 2000 | 0.213 [0.204, 0.222] | 0.096 [0.089, 0.102] | True |
| small_world | 30 | 250 | 0.072 [0.063, 0.081] | -0.032 [-0.044, -0.019] | False |
| small_world | 30 | 500 | 0.131 [0.123, 0.140] | -0.032 [-0.039, -0.026] | False |
| small_world | 30 | 1000 | 0.183 [0.175, 0.191] | 0.045 [0.038, 0.051] | True |
| small_world | 30 | 2000 | 0.210 [0.202, 0.218] | 0.089 [0.083, 0.094] | True |

## Q1 -- EBICglasso precision by N

| structure | p | precision by N | trend |
|---|---|---|---|
| clustered | 10 | 250: 0.929, 500: 0.889, 1000: 0.848, 2000: 0.840 | decreasing |
| clustered | 20 | 250: 0.909, 500: 0.853, 1000: 0.812, 2000: 0.790 | decreasing |
| clustered | 30 | 250: 0.873, 500: 0.821, 1000: 0.770, 2000: 0.740 | decreasing |
| random_dense | 10 | 250: 0.887, 500: 0.839, 1000: 0.803, 2000: 0.793 | decreasing |
| random_dense | 20 | 250: 0.709, 500: 0.691, 1000: 0.686, 2000: 0.675 | decreasing |
| random_dense | 30 | 250: 0.849, 500: 0.717, 1000: 0.706, 2000: 0.707 | decreasing |
| random_sparse | 10 | 250: 0.930, 500: 0.898, 1000: 0.872, 2000: 0.848 | decreasing |
| random_sparse | 20 | 250: 0.831, 500: 0.770, 1000: 0.729, 2000: 0.717 | decreasing |
| random_sparse | 30 | 250: 0.751, 500: 0.666, 1000: 0.640, 2000: 0.624 | decreasing |
| random_with_isolates | 10 | 250: 0.952, 500: 0.928, 1000: 0.916, 2000: 0.911 | decreasing |
| random_with_isolates | 20 | 250: 0.903, 500: 0.857, 1000: 0.818, 2000: 0.797 | decreasing |
| random_with_isolates | 30 | 250: 0.796, 500: 0.743, 1000: 0.709, 2000: 0.688 | decreasing |
| small_world | 10 | 250: 0.848, 500: 0.820, 1000: 0.781, 2000: 0.782 | decreasing |
| small_world | 20 | 250: 0.881, 500: 0.821, 1000: 0.775, 2000: 0.761 | decreasing |
| small_world | 30 | 250: 0.899, 500: 0.835, 1000: 0.789, 2000: 0.765 | decreasing |

## Q3 -- GOPC vs non-regularized (MCC)

- **clustered**: nonreg_holm: {'better': 5, 'comparable': 1, 'worse': 3}; nonreg_bh: {'worse': 7, 'comparable': 2}
- **random_dense**: nonreg_holm: {'better': 6, 'comparable': 1, 'worse': 2}; nonreg_bh: {'worse': 6, 'comparable': 2, 'better': 1}
- **random_sparse**: nonreg_holm: {'better': 5, 'comparable': 2, 'worse': 2}; nonreg_bh: {'worse': 6, 'comparable': 2, 'better': 1}
- **random_with_isolates**: nonreg_holm: {'comparable': 5, 'better': 4}; nonreg_bh: {'worse': 3, 'comparable': 5, 'better': 1}
- **small_world**: nonreg_holm: {'better': 5, 'comparable': 1, 'worse': 3}; nonreg_bh: {'worse': 7, 'comparable': 2}

## Q4 -- one default vs one PC alpha: **DOES NOT REPLICATE**

- N=250: {"selected_pc": "pc@0.05", "cells": 15, "pc_selected_comparable_or_better": 13, "gopc_comparable_or_better": 2, "some_single_pc_alpha_matches_everywhere": false}
- N=500: {"selected_pc": "pc@0.05", "cells": 15, "pc_selected_comparable_or_better": 13, "gopc_comparable_or_better": 3, "some_single_pc_alpha_matches_everywhere": false}
- N=1000: {"selected_pc": "pc@0.05", "cells": 15, "pc_selected_comparable_or_better": 12, "gopc_comparable_or_better": 5, "some_single_pc_alpha_matches_everywhere": false}
- N=2000: {"selected_pc": "pc@0.01", "cells": 15, "pc_selected_comparable_or_better": 12, "gopc_comparable_or_better": 6, "some_single_pc_alpha_matches_everywhere": false}

## Q5 -- mechanism

- screen removes < 50% of true non-edges without isolates (N >= 1000): False
- screen's share larger with isolates: True

## Q6 -- weights: **RECOMMEND REFIT** (refit better in 0.956 of counted cells)

## Q7 -- runtime: see `report.json` (`q7`).

Figures: `precision_vs_n.png`, `sensitivity_vs_specificity.png`, `truth_strength.png`.
