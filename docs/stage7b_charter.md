# Stage 7b Charter: External Validity — GOPC vs EBICglasso, PC and Non-Regularized Testing on Psych-Realistic Networks

Status: **DRAFT — not frozen.** Blocked on Stage 7a's decision-log entry,
which fixes `gopc_engine` below. Freeze (status line, date, SHA-256
recorded by the runner) happens after the timing smoke and before any
full run, per `docs/development_plan/README.md`.
Date: 2026-09-22

"Stage 7" continues this repository's own charter sequence. It is
unrelated to the retired MINT outline's "Stage 7" / "Stage 8".

## Background and objective

GOPC's stated niche (D-065, `docs/handoff/2026-09-22_gopc.md`) has two
parts:

- It fixes EBICglasso's demonstrated weakness, which is that its
  precision collapses as true signal strengthens (D-050, D-054).
- It does so with one fixed default that does not need per-dataset
  tuning (D-065 Q3).

All of that evidence comes from two composed `p = 15` networks and three
`p = 3` triangles. In `chain_fork_hub`, 6 of 15 variables are pure noise,
independent of everything. Psychological item sets almost never contain
such variables. GOPC's `alpha(N)` was also calibrated on the same motif
family (D-065's fairness disclosure). D-065 attributes GOPC's precision
to its strict marginal screen. On densely inter-correlated data that
screen may pass most pairs: a one-replicate probe in the 2026-09-22
review saw 71% of pairs pass at `p = 20`, density `.35`, `N = 300`.
Whether the niche survives outside the motif family is the most
consequential open question in the project.

**Objective.** On random, psych-realistic Gaussian graphical models
(`gopcnet.generators.psych_networks`), with `p` up to 30 and `N` from 250
to 2000, test the following with predeclared readings:

- (Q1) whether EBICglasso's weakness exists there at all
- (Q2) whether GOPC's default beats it on precision without losing too
  much F1
- (Q3) how GOPC compares with non-regularized full-order testing, the
  field's standard higher-specificity alternative
- (Q4) whether D-065's "one default versus per-regime PC alpha" finding
  replicates out of sample
- (Q5) whether the precision mechanism (screen vs prune) transfers
- (Q6) which edge-weight convention recovers the true partial
  correlations better
- (Q7) runtime

**What this charter is not.**

- No new alpha rules (Stage 7c).
- No ordinal data (Stage 7e).
- No empirical-data-derived truths (a separate, optional follow-up).
- No tuning of any method on this charter's data, except Q4's
  predeclared development-set PC-alpha selection.
- No claims below `N = 500`. `N = 250` is characterization only.

## Design

### Truth structures (`gopcnet.generators.psych_networks`; Cholesky sampler, D-067)

| Structure | Graph | Notes |
|---|---|---|
| `random_sparse` | Erdős–Rényi, density .20 | |
| `random_dense` | Erdős–Rényi, density .35 | Positive-definiteness shrinkage reduces edge strength at large `p` (mean `\|P\|` about .11 at `p = 30`, against about .19 elsewhere). Reported, not corrected. |
| `small_world` | Watts–Strogatz, `k = 4`, rewire .1 | Density falls with `p` (.44 / .21 / .14) |
| `clustered` | Stochastic block, `round(p / 5)` blocks, within .6, between .05 | |
| `random_with_isolates` | ER .20 on 75% of nodes, 25% isolated | The legacy noise-column regime, as a manipulated factor |

Edge weights: 70% in `[.08, .20]`, 30% in `[.20, .40]`, 15% negative.
The true partial correlations `P` are known exactly.

**Anchor:** `legacy_chain_fork_hub` (Stage 5a's frozen sampler, strength
`.5`, `p = 15`) at `N in {1000, 1500}`, used only for gate G3.

### Grid

- `p in {10, 20, 30}` x `N in {250, 500, 1000, 2000}` x 5 structures =
  60 cells, plus the 2 anchor cells.
- **Replicates:** set by the timing rule below (target 500, floor 200).
  The first half is development, the second half validation.
- **Truth per replicate, paired across `N`:**
  - truth seed:
    `SeedSequence([20260830, 702, structure_index, p_index, replicate, 0])`
  - data seed:
    `SeedSequence([20260830, 702, structure_index, p_index, replicate, 1, n_index])`

  A given replicate therefore uses the same true network at every
  sample size.
- **Anchor seeds:** Stage 5a's own `_condition_seed` for
  `chain_fork_hub` on Stage 5a's full `N` grid, so the anchor draws
  equal the archived Stage 5g draws.

### Methods (all fitted on the same draw)

| Label | Fit |
|---|---|
| `gopc` | `fit_gopc(data, engine=<gopc_engine>)` with **default alphas** (`gopcnet.defaults`, D-068). At `N in {250, 500}` the pruning alpha is extrapolated (about .21 and .17); that is the point, so the warning is recorded and the cell is kept. |
| `gopc_component` | `fit_gopc(data)` with the frozen engine, `p = 10` only: a bridge to the validated mechanism |
| `pc@.001`, `pc@.005`, `pc@.01`, `pc@.05` | `pc_stable_skeleton(corr, N, alpha)` |
| `pc_frozen@.01` | `fit_pc_skeleton(data, alpha=.01)`, gate G1 only, on the first 30 replicates of cells with `p <= 20` |
| `ebicglasso` | `fit_ebicglasso(data)`, `gamma = .5` (qgraph's default; frozen) |
| `nonreg_holm` | `fit_nonregularized_ggm(data, alpha=.05, correction="holm")` |
| `nonreg_bh` | `fit_nonregularized_ggm(data, alpha=.05, correction="bh")` |

`gopc_engine` is `"adjacency"` if Stage 7a's decision-log entry records
Q1 NON-INFERIOR for all five legacy shapes. Otherwise this charter is
revised with the user before freezing. With the component engine it
would run at `p <= 20` only.

### Metrics per `(replicate, method)`

- **Structure:** sensitivity (= recall), specificity, precision, F1,
  MCC, `n_estimated_edges`, SHD. MCC is
  `(TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))`, NaN if the
  denominator is 0.
- **Weights, native:** Pearson correlation and MAE between the method's
  native weight vector and the true `P`, over all `p(p-1)/2` pairs.
  Native weights are GOPC's D-055 min-subset weights, EBICglasso's
  shrunken partial correlations, and the non-regularized full-order
  values. PC has none (NaN).
- **Weights, refit:** the same two metrics after
  `refit_weights(data, adjacency)`, for every method, on one common
  scale.
- **Centrality:** Spearman correlation between estimated and true node
  strength (`sum_j |w_ij|`) using refit weights. NaN if either vector is
  constant.
- **GOPC mechanism diagnostics** (`gopc` only):
  - `screen_pass_fraction`
  - `null_removed_by_screen` and `null_removed_by_prune`: true
    non-edges removed at each stage, as a share of all true non-edges
  - `true_edges_lost_at_screen`, `true_edges_lost_at_prune`
  - total tests
  - `cap_reached` count
- **Truth descriptors:** `truth_hash`, shrinkage `c`, the true edge
  count, the mean `|P|` over true edges.
- `elapsed_seconds`, `status`, `error`.

### Replicate-count rule (the only thing the timing smoke may set)

1. Run the smoke with 5 replicates per cell and all methods.
2. Let `t_cell` be the projected seconds per replicate for the slowest
   cell. Expect `random_dense` at `p = 30`: EBICglasso's 100-point path,
   plus about 20 s for the adjacency engine (Stage 7a smoke).
3. `R = min(500, floor(4.0 h x 3600 / t_cell))`, rounded down to a
   multiple of 50, with a floor of 200. If `R < 200` would be needed,
   stop and ask the user.
4. Record `R` in an implementation-time amendment before the full run.

## Decision structure

**Gates (pipeline integrity). If any fails, stop.**

- **G1:** `pc@.01` equals `pc_frozen@.01` (`edge_bits` identical) on at
  least 99.9% of the G1 subsample.
- **G2:** truth pairing. For every `(structure, p, replicate)`,
  `truth_hash` is identical across all `N`. Every truth satisfies the
  positive-definiteness margin.
- **G3:** anchor continuity. On `legacy_chain_fork_hub`, `gopc_component`
  with explicit `(.001, default_dpi_alpha(N))` matches the archived
  Stage 5g `gopc_growing_subset` cell means for precision and recall
  (`evidence/stage5_benchmarks/stage5g_growing_subset/raw_metrics.csv`)
  at `N in {1000, 1500}`, with unpaired `|z| <= 3`. A row-wise
  agreement fraction is reported as a bonus, not gated.

**Descriptive questions, with predeclared readings.**

All questions use validation replicates. Cell verdicts are counted
*within each structure*, over its 9 cells with `N >= 500`. Every paired
comparison reports the mean paired difference and a 95% percentile
bootstrap CI (2,000 resamples of replicate indices). `N = 250` is
reported separately as characterization only.

- **Q1 — Does EBICglasso's weakness exist here?** EBICglasso's precision
  and specificity versus `N`, per structure and `p`, with the trend
  classified as increasing, flat or decreasing using D-050's method. If
  EBICglasso's precision is `>= .95` in most cells, the report states
  plainly that the problem GOPC fixes is not present in these regimes.
- **Q2 — primary niche claim (GOPC vs EBICglasso).** A cell supports the
  niche if both hold:
  - (i) the paired `precision_gopc - precision_ebic` CI lies entirely
    above `.05`
  - (ii) the paired `F1_gopc - F1_ebic` CI lower bound is `>= -.02`

  Per structure: **HOLDS** if 7 or more of 9 cells support it,
  **PARTIAL** if 3–6 do, **FAILS** if 2 or fewer do.
- **Q3 — GOPC vs non-regularized testing.** Per cell, `MCC_gopc` against
  each of `nonreg_holm` and `nonreg_bh`:
  - "better": the CI lies entirely above `.01`
  - "worse": the CI lies entirely below `-.01`
  - "comparable": otherwise

  Counts are reported per structure. Sensitivity and specificity are
  also reported separately.
- **Q4 — one default vs one PC alpha (D-065 Q3, out of sample).**
  - On development replicates, for each `N`, select the single PC alpha
    from `{.001, .005, .01, .05}` with the highest mean MCC across all
    `(structure, p)` combinations, weighted equally.
  - On validation replicates, count the cells where `pc@selected` is
    comparable or better than GOPC (MCC CI lower bound `>= -.01`), and
    the reverse.
  - **REPLICATES** if, at 3 or more of the 4 `N`, no single PC alpha is
    comparable or better in every combination *and* GOPC is comparable
    or better than `pc@selected` in at least 80% of cells. Otherwise
    **DOES NOT REPLICATE**.
- **Q5 — does the mechanism transfer?** Mean `null_removed_by_screen`
  and `null_removed_by_prune` per structure, `p` and `N`. Two
  predictions, each reported as held or not held:
  - in the four structures without isolates, at `N >= 1000`, the screen
    removes less than 50% of true non-edges
  - in `random_with_isolates`, the screen's share is materially larger
- **Q6 — weight convention.** For GOPC, compare the native
  (min-subset) and refit weight MAE against `P`, per cell.
  **RECOMMEND REFIT** if the refit MAE is lower, with the CI entirely
  below 0, in at least 75% of validation cells with `N >= 500`. The
  switch itself needs its own decision-log entry, as a successor to
  D-055.
- **Q7 — runtime.** Median and 90th-percentile seconds per method, `p`
  and `N`. Descriptive. This corrects D-047's "orders of magnitude
  faster" claim to its actual scope.

## Consequences (predeclared routing)

| Outcome | Condition | Consequence |
|---|---|---|
| **A: niche confirmed** | Q2 HOLDS in at least 3 of the 4 non-isolate structures, and Q3 is not "worse" in a majority of cells for both non-regularized variants | The paper keeps the D-065 framing, now with external validity. Proceed to Phase 2 as written. Consider making `engine="adjacency"` the default (its own entry). |
| **B: noise-variable niche only** | Q2 HOLDS or is PARTIAL in `random_with_isolates` but FAILS in most non-isolate structures | Restate the contribution: GOPC helps when the variable set includes irrelevant or weakly connected variables. Ask the user before Phase 2. |
| **C: non-regularized dominates** | Q3 "worse" in a majority of cells for either non-regularized variant, across 3 or more structures | EBICglasso's weakness is fixed by non-regularized testing in general. Ask the user; the paper's thesis changes. |
| **D: niche fails** | Q2 FAILS in 3 or more structures, including `random_with_isolates` | Ask the user. Stop feature work and report as a scoping result. |
| Mixed / other | anything else | Report per the branches above and ask the user. |

Either way, a decision-log entry (the next free number) records the
gates, Q1–Q7, the routing outcome, this charter's SHA-256 and the
evidence link. `docs/validated_operating_ranges.md` gains an "External
validity (Stage 7b)" section scoped to `p <= 30`, Gaussian data, these
five structure families and `N >= 500`.

## Sharding

The runner shards on `--structures` x `--ps` x `--sample-sizes` (the
workflow's three-dimension mode). A shard whose filters select no cells,
for example the anchor structure at `p != 15`, writes a header-only
`raw_metrics.csv` and exits 0. Dispatching the workflow requires the
user's explicit go-ahead.

## Required evidence

- the resolved configuration
- this charter's SHA-256, recorded at freeze by the runner's
  `metadata.json`
- commit and runtime metadata
- raw per-replicate rows for every cell, with no cell omitted
- `report.json`, with machine-readable verdicts for every gate and
  question
- `stage7b_report.md`, with the full per-structure tables and the
  `N = 250` section
- figures:
  - precision versus `N` per method, faceted by structure x `p`
  - sensitivity versus specificity
  - the Q5 screen/prune shares
  - runtime versus `p`
  - the realized true-weight distribution by structure

Archived under `evidence/stage7_external_validity/stage7b_benchmark/`.
Split any raw file over 45 MB into parts under 45 MB, to stay under
GitHub's recommended per-file size.

## Resolutions of the pre-freeze questions

*(To be filled in at freeze: the Stage 7a outcome and `gopc_engine`, the
replicate count from the timing rule, and the shard plan. Each is
recorded with its reason, before any full run.)*
