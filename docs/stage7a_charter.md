# Stage 7a Charter: Adjacency-Set GOPC Engine — Non-Inferiority on the Legacy Shapes and Runtime Scaling

Status: **FROZEN before results** (smoke run only: gates and timing,
no outcome metric used to set anything; see the final section).
Date: 2026-09-22

"Stage 7" here continues this repository's own charter sequence
(`stage6a` was the last). It is unrelated to the "Stage 7" / "Stage 8"
of the retired MINT outline cited in `docs/stage5a_charter.md`.

## Background and objective

`fit_gopc`'s frozen pruning engine (`growing_subset_dpi`, D-053) draws
conditioning sets from the edge's whole connected component in the
screened graph, fixed after screening. When screening passes most pairs,
as it does for densely inter-correlated psychological item sets, that
means every subset of up to 4 of the other `p - 2` variables. For
example, `C(28, <=4)` is about 24,000 per edge at `p = 30`. The
2026-09-22 review measured one fit at 204 s (`p = 20`, density `.35`,
`N = 300`), against 0.8 s for PC. The external-validity benchmark
(Stage 7b) needs `p = 30`, which is out of reach at that cost.

D-065's Q4 found that GOPC's pruning at matched alpha is effectively
PC's own search restricted to the screened graph. The adjacency engine
(`fit_gopc(..., engine="adjacency")`, built on
`gopcnet.pipeline.skeleton_core.pc_stable_skeleton`) makes that
explicit. It runs PC-stable on the screened graph, from level 1 up to
`max_conditioning_size`, and draws conditioning sets from each
endpoint's *current* neighbors, which shrink as edges are pruned. Under
PC's own assumptions (faithfulness), a separating set, when one exists,
lies within one endpoint's adjacency set, so the adjacency pool is
sufficient in principle. It tests far fewer sets, which may also mean
fewer chances for an underpowered test to wrongly prune a weak true
edge.

**Objective.**

1. Test whether the adjacency engine is *non-inferior* to the frozen
   component engine in precision and recall on the five legacy shapes
   the component engine was validated on.
2. Measure how both engines' runtime scales with `p` on the new
   psych-realistic structures.

**What this charter is not.**

- It does not change `fit_gopc`'s default engine. That needs its own
  decision-log entry after Stage 7b.
- It does not compare against EBICglasso or test external validity
  (Stage 7b).
- It does not tune `max_conditioning_size` or either alpha.

## Design

### Part A — legacy shapes (non-inferiority)

- **Shapes:** the five Stage 5a DGPs through their frozen samplers
  (`gopcnet.experiments.stage5a._DGP_REGISTRY`): `chain_fork_hub`,
  `overlap`, `triangle_balanced`, `triangle_moderate`,
  `triangle_strong`. Strength `.5`.
- **Sample sizes:** `N in {750, 1000, 1500, 1750}`, the validated range
  used in Stage 5h/5i.
- **Replicates:** 1,000 per cell (development `0`–`499`, validation
  `500`–`999`).
- **Seeds:** a fresh, disjoint derivation,
  `SeedSequence([20260830, 701, dgp_index, n_index, replicate])`. Both
  engines are fitted on the **same draw** inside this run, so the
  comparison is paired and does not depend on any archive. The
  `overlap` sampler's cross-machine non-reproducibility (D-065) cannot
  affect it.
- **Methods, per draw:**

  | Label | Fit |
  |---|---|
  | `gopc_component` | `fit_gopc(data, screening_alpha=.001, dpi_alpha=default_dpi_alpha(N), max_conditioning_size=4)`, the frozen engine |
  | `gopc_adjacency` | the same call with `engine="adjacency"` |
  | `pc_frozen` | `fit_pc_skeleton(data, alpha=.01)`, for gate G1 |
  | `pc_core` | `pc_stable_skeleton(corrcoef(data), N, .01).adjacency`, for gate G1 |

### Part B — runtime scaling (descriptive)

- **Structures:** `random_sparse`, `random_dense` and `clustered` from
  `gopcnet.generators.psych_networks` (Cholesky sampler, D-067).
- **Grid:** `p in {10, 20, 30}`, `N = 500`, 20 replicates.
- **Seeds:** truth seed
  `SeedSequence([20260830, 701, 100 + structure_index, p_index, replicate, 0])`;
  data seed with a trailing `1`.
- **Methods:** `gopc_component` and `gopc_adjacency` with default alphas
  (`resolve_alphas(500, p)`; the range warning at `N = 500` is expected
  and recorded, not suppressed).
- **Time budget:** each `gopc_component` fit gets 60 s, enforced by
  running it in a child process that is terminated on expiry. A
  timed-out fit is recorded as `status = "timeout"`, meaning the engine
  is **infeasible** at that size. It is not an error and is not
  retried. `gopc_adjacency` runs in-process without a budget; a fit over
  60 s is reported as such.

**Realized truth strength.** At `p = 30`, `random_dense` needs a
positive-definiteness shrinkage factor of about `.57`, so its mean
`|partial correlation|` is about `.11`, against about `.19` elsewhere
(checked while building the generators). This does not affect a runtime
comparison, but the report states it so the same design fact is not
misread in Stage 7b.

## Metrics

Per `(replicate, method)`:

- `precision`, `recall`, `f1`, `shd`, `n_estimated_edges`, from
  `stage5a._graph_metrics` (Part A; Part B scored the same way against
  the truth)
- `edge_bits` (hex upper triangle, `stage5i.encode_edges`)
- `n_tests_total` (adjacency engine; NaN for the others)
- `elapsed_seconds`
- `status` / `error`

## Decision structure

**Gates (pipeline integrity).** If either fails, stop and resolve
before interpreting anything else.

- **G1:** `pc_core` reproduces `pc_frozen`'s adjacency (`edge_bits`
  identical) in at least 99.9% of Part A rows, across all shapes.
- **G2:** the correlation-matrix primitive and the skeleton core pass
  their unit tests (`tests/unit/test_correlation_based.py`,
  `tests/unit/test_skeleton_core.py`) at the run's recorded commit.

**Q1 — non-inferiority (Part A, validation replicates, per
`(shape, N)` cell).**

- Compute the paired `precision_adjacency - precision_component` and
  `recall_adjacency - recall_component`, each with a 95% percentile
  bootstrap CI (2,000 resamples of replicate indices, seed `701`).
  Replicates where precision is undefined for either engine (no edges
  estimated) are excluded from the precision difference only, and the
  count is reported.
- A cell is **non-inferior** if the CI lower bound is `>= -.02` for
  both metrics. `.02` is Stage 5g's recall-regression tolerance (D-053).
- Verdict per shape:
  - **NON-INFERIOR** if all 4 cells pass
  - **MIXED** if 2–3 pass
  - **INFERIOR** if 0–1 pass
- **Descriptive (not a gate):** the same paired differences reported as
  point estimates, including any cell where the adjacency engine is
  *better* by more than `.02`.

**Q2 — agreement (Part A, descriptive).** The mean per-replicate
symmetric edge difference between the two engines, against a
same-engine noise floor. The noise floor is the component engine
refitted at `dpi_alpha x 1.25`, D-065 Q4's method, fitted on the
validation replicates of each cell.

**Q3 — runtime (Part B, descriptive).**

- Median and 90th-percentile seconds per fit, per
  `(structure, p, engine)`.
- The share of `gopc_component` fits that timed out.
- Mean `n_tests_total` for the adjacency engine.
- Structural agreement between the engines wherever both finished.

## Explicit non-goals

- No change to `fit_gopc`'s default engine.
- No comparison with EBICglasso, the non-regularized comparator, or PC
  beyond gate G1.
- No new alpha rules, no tuning of `max_conditioning_size`.
- No claims below `N = 750` from Part A; Part B's `N = 500` is a
  runtime setting, not an accuracy claim.
- No non-Gaussian data.

## Sharding

Part A is sharded by `--dgps` × `--sample-sizes` (20 cells). Part B is
sharded by `--structures` × `--ps` (9 cells). Both run through
`.github/workflows/sharded_benchmark.yml` using the `--parts` flag as
the first dimension. Shards whose filters select no cells write a
header-only `raw_metrics.csv` and exit 0. If a local run finishes in
under two hours, it may run locally instead, and the report records
which.

## Required evidence

- the resolved configuration
- this charter's SHA-256, recorded at freeze by the runner's
  `metadata.json`
- commit and runtime metadata
- raw per-replicate rows for every cell, with no cell omitted
- a report presenting G1, G2, Q1 (with a forest plot per shape), Q2 and
  Q3 (with a runtime-vs-`p` figure on a log axis)

Archived under `evidence/stage7_scalable_engine/stage7a_engine/`.

## Consequences

- **G1 and G2 pass and Q1 is NON-INFERIOR for all five shapes:**
  Stage 7b uses `engine="adjacency"` as "GOPC". The component engine
  appears in Stage 7b only at `p = 10`, as a bridge to the frozen
  mechanism. `fit_gopc`'s default is unchanged by this result alone; a
  default switch needs its own decision-log entry, informed by
  Stage 7b.
- **Q1 is MIXED or INFERIOR for any shape:** stop and ask the user.
  The options are (a) run Stage 7b with the component engine at
  `p <= 20` only, or (b) diagnose first, e.g. with a D-052-style
  attribution of the adjacency engine's extra errors.
- **Either way:** a decision-log entry (the next free number) with this
  charter's SHA-256 and a link to the evidence directory.

## Resolutions of the pre-freeze questions

Recorded at freeze, 2026-09-22, from the smoke configuration
(`configs/stage7a_engine_smoke.yaml`: 10 Part A replicates per cell, 3
Part B replicates per cell; run locally, about 2 minutes, 0 errors).
Only gates, feasibility and timings were read. Q1/Q2 outcome metrics
were not used to set anything.

1. **Gates compute and pass on the smoke data.** G1: identical fraction
   `1.0000` over 200 rows. G2: max difference `5.6e-16` over 200 random
   checks.
2. **Part B budget and replicates: unchanged** (60 s, 20 replicates).
   The smoke showed the component engine exceeding 60 s on every
   `random_sparse`/`random_dense` fit at `p >= 20` (and 2 of 3 at
   `clustered`, `p = 30`). The adjacency engine finished every fit,
   with a median of about 0.8–3.4 s, except `random_dense` at `p = 30`
   (about 20 s, about 164,000 tests per fit). Those timeouts are the
   result Part B exists to measure, not a reason to change the design.
   Worst case, Part B costs 20 x 9 x 60 s of component-engine time,
   spread across local workers.
3. **Run location: local.** Part A fits take about 0.005–0.02 s each, so
   Part A's 100,000 fits and Part B's worst case both fit comfortably
   inside the charter's two-hour local allowance. No sharded CI run is
   needed. The report records the machine (`metadata.json`: platform,
   CPU count).
4. **Noted for Stage 7b (not a change here):** the adjacency engine's
   cost on `random_dense` at `p = 30` (about 20 s per fit) sets that
   charter's compute budget and should be accounted for in its
   replicate-count rule.
