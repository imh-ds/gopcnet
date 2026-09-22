# Stage 6a report: edge-evidence tiers and bridge inference

Charter: `docs/stage6a_charter.md` (FROZEN before results). All comparisons use validation replicates only.

## G1 (pipeline integrity)

- **G1**: PASSED -- mean survival-vs-pMax top-1 agreement 0.9644 (threshold 0.95); worst cell 0.05|0.4|500 at 0.791

## Q1 -- survival-fraction ranking vs marginal-correlation ranking

29 of 60 cells meet the >= .20 margin (0.48 fraction, threshold 0.8): **does not confirm** the preliminary scratch finding.

## Q2 -- does detection power scale with N and bridge strength as expected?

- **confound_trap_latent**: monotonic non-decreasing in N: True ({500: 0.8624999999999999, 750: 0.8802500000000001, 1000: 0.8986666666666666, 1500: 0.9213333333333334, 3000: 0.9673333333333334})
- **confound_trap_observed**: monotonic non-decreasing in N: True ({500: 0.8818333333333334, 750: 0.90275, 1000: 0.9129166666666667, 1500: 0.9403333333333332, 3000: 0.9805})
- **double_bridge**: monotonic non-decreasing in N: True ({500: 0.7797916666666667, 750: 0.8417083333333334, 1000: 0.8750416666666667, 1500: 0.9240416666666667, 3000: 0.9771666666666667})
- **larger_clusters**: monotonic non-decreasing in N: True ({500: 0.8445, 750: 0.8775833333333334, 1000: 0.89875, 1500: 0.93775, 3000: 0.98425})

## Q3 -- does the false-confirmation rate behave as predicted?

- **confound_trap_observed**: {500: 0.0188125, 750: 0.017125, 1000: 0.01615625, 1500: 0.01259375, 3000: 0.007291666666666666}, ratio (low N / high N) = 2.58
- **confound_trap_latent**: {500: 0.09379166666666668, 750: 0.10536458333333333, 1000: 0.10885416666666665, 1500: 0.1136875, 3000: 0.11783333333333335}, ratio (low N / high N) = 0.795968882602546
- **Verdict**: does not match the predeclared pattern -- limitation restated per the actual result

## Q4 -- does a larger conditioning pool degrade detection?

Mean recovery difference (larger_clusters minus confound_trap_observed): -0.0151
larger_clusters uses RHO_WITHIN_LARGE_CLUSTER=0.25 vs 0.30 for confound_trap_observed (implementation-time amendment, see charter) -- direct comparison is disclosed, not a clean ceteris-paribus contrast.

## Q5 -- double_bridge joint recovery

Per-bridge recovery vs. single-bridge shape and exact-joint recovery are in `report.json`.

## Bootstrap calibration

- **confound_trap_observed**: bridge confirmed rate 0.65, decoy confirmed rate 0.05, correctly ordered: True
- **confound_trap_latent**: bridge confirmed rate 0.63, decoy confirmed rate 0.10, correctly ordered: True

Full validation grid: `full_grid_validation.csv`. Figure: `false_confirm_rate_vs_n.png`.
