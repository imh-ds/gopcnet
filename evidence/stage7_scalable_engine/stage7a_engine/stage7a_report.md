# Stage 7a report: adjacency-set GOPC engine

Charter: `docs/stage7a_charter.md`. Q1/Q2 use validation replicates only.

## Gates

- **G1** (`pc_core` reproduces `pc_frozen`): PASSED -- identical fraction 1.0000 over 20000 rows (bar 0.999).
- **G2** (correlation primitive equals frozen primitive): PASSED -- max |difference| 5.55e-16 over 200 random checks.

## Q1 -- non-inferiority (adjacency minus component; margin -0.02 on both metrics)

- **chain_fork_hub**: NON-INFERIOR (4/4 cells)
- **overlap**: NON-INFERIOR (4/4 cells)
- **triangle_balanced**: NON-INFERIOR (4/4 cells)
- **triangle_moderate**: NON-INFERIOR (4/4 cells)
- **triangle_strong**: NON-INFERIOR (4/4 cells)

| shape | N | precision diff [95% CI] | recall diff [95% CI] | non-inferior |
|---|---|---|---|---|
| chain_fork_hub | 750 | -0.0005 [-0.0012, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| chain_fork_hub | 1000 | -0.0002 [-0.0005, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| chain_fork_hub | 1500 | -0.0003 [-0.0009, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| chain_fork_hub | 1750 | -0.0004 [-0.0011, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| overlap | 750 | -0.0019 [-0.0030, -0.0009] | 0.0000 [0.0000, 0.0000] | True |
| overlap | 1000 | -0.0026 [-0.0040, -0.0014] | 0.0000 [0.0000, 0.0000] | True |
| overlap | 1500 | -0.0077 [-0.0100, -0.0057] | 0.0000 [0.0000, 0.0000] | True |
| overlap | 1750 | -0.0079 [-0.0104, -0.0057] | 0.0000 [0.0000, 0.0000] | True |
| triangle_balanced | 750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_balanced | 1000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_balanced | 1500 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_balanced | 1750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_moderate | 750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_moderate | 1000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_moderate | 1500 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_moderate | 1750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_strong | 750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_strong | 1000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_strong | 1500 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |
| triangle_strong | 1750 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | True |

## Q2 -- engine agreement (mean symmetric edge difference per replicate)

| shape | N | adjacency vs component | noise floor (component at 1.25 x alpha) |
|---|---|---|---|
| chain_fork_hub | 750 | 0.004 | 0.092 |
| chain_fork_hub | 1000 | 0.002 | 0.090 |
| chain_fork_hub | 1500 | 0.002 | 0.074 |
| chain_fork_hub | 1750 | 0.004 | 0.060 |
| overlap | 750 | 0.024 | 0.138 |
| overlap | 1000 | 0.030 | 0.108 |
| overlap | 1500 | 0.088 | 0.110 |
| overlap | 1750 | 0.092 | 0.088 |
| triangle_balanced | 750 | 0.000 | 0.000 |
| triangle_balanced | 1000 | 0.000 | 0.000 |
| triangle_balanced | 1500 | 0.000 | 0.000 |
| triangle_balanced | 1750 | 0.000 | 0.000 |
| triangle_moderate | 750 | 0.000 | 0.008 |
| triangle_moderate | 1000 | 0.000 | 0.002 |
| triangle_moderate | 1500 | 0.000 | 0.000 |
| triangle_moderate | 1750 | 0.000 | 0.000 |
| triangle_strong | 750 | 0.000 | 0.038 |
| triangle_strong | 1000 | 0.000 | 0.028 |
| triangle_strong | 1500 | 0.000 | 0.020 |
| triangle_strong | 1750 | 0.000 | 0.012 |

## Q3 -- runtime (N = 500; component budget 60 s per fit)

| structure | p | method | fits | timeouts | errors | median s | p90 s | mean tests | mean F1 |
|---|---|---|---|---|---|---|---|---|---|
| clustered | 10 | gopc_adjacency | 20 | 0 | 0 | 0.01 | 0.08 | 79 | 0.747 |
| clustered | 10 | gopc_component | 20 | 0 | 0 | 0.13 | 4.16 | n/a | 0.747 |
| clustered | 20 | gopc_adjacency | 20 | 0 | 0 | 0.08 | 0.30 | 395 | 0.800 |
| clustered | 20 | gopc_component | 20 | 9 | 0 | 7.73 | 44.42 | n/a | 0.786 |
| clustered | 30 | gopc_adjacency | 20 | 0 | 0 | 0.31 | 0.71 | 1625 | 0.793 |
| clustered | 30 | gopc_component | 20 | 19 | 0 | 2.19 | 2.19 | n/a | 0.843 |
| random_dense | 10 | gopc_adjacency | 20 | 0 | 0 | 0.09 | 0.24 | 401 | 0.871 |
| random_dense | 10 | gopc_component | 20 | 0 | 0 | 2.22 | 3.93 | n/a | 0.872 |
| random_dense | 20 | gopc_adjacency | 20 | 0 | 0 | 3.46 | 6.71 | 12858 | 0.782 |
| random_dense | 20 | gopc_component | 20 | 20 | 0 | n/a | n/a | n/a | n/a |
| random_dense | 30 | gopc_adjacency | 20 | 0 | 0 | 28.27 | 57.46 | 115923 | 0.666 |
| random_dense | 30 | gopc_component | 20 | 20 | 0 | n/a | n/a | n/a | n/a |
| random_sparse | 10 | gopc_adjacency | 20 | 0 | 0 | 0.01 | 0.03 | 51 | 0.847 |
| random_sparse | 10 | gopc_component | 20 | 0 | 0 | 0.22 | 0.82 | n/a | 0.850 |
| random_sparse | 20 | gopc_adjacency | 20 | 0 | 0 | 0.38 | 1.60 | 1971 | 0.829 |
| random_sparse | 20 | gopc_component | 20 | 15 | 0 | 26.56 | 51.05 | n/a | 0.809 |
| random_sparse | 30 | gopc_adjacency | 20 | 0 | 0 | 4.74 | 7.48 | 16110 | 0.768 |
| random_sparse | 30 | gopc_component | 20 | 20 | 0 | n/a | n/a | n/a | n/a |

Figures: `q1_non_inferiority.png`, `q3_runtime_vs_p.png`.
