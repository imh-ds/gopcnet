# GOPC Development Plan (post-D-065)

Status: **PLAN, not a charter.** Nothing here is frozen evidence or an
authorized run. Each phase document tells an agent exactly what to
build and what to charter. Every simulation it describes still needs
its own frozen charter in `docs/` (following the existing
`docs/stageNx_charter.md` convention) before any full-scale run.

Written: 2026-09-22, after reviewing `docs/handoff/2026-09-22_gopc.md`,
`docs/decision_log.md` D-047 through D-065, the Stage 5i evidence, the
Stage 6a charter, and the core GOPC code.

## Why this plan exists

GOPC's stated niche (handoff, "What GOPC is for") has two parts:

1. Fix EBICglasso's demonstrated weakness: its precision collapses as
   true signal strengthens (D-050, D-054).
2. Stay as practical as EBICglasso for applied psychology: one default
   that works without per-dataset tuning (D-065), weighted edges, no
   causal framing.

The evidence behind both claims is **internally strong but externally
narrow**:

- Two composed `p = 15` networks and three `p = 3` triangles. In
  `chain_fork_hub`, 6 of 15 variables are pure noise, independent of
  everything. Psychological item sets almost never contain such
  variables.
- `alpha(N)` (D-012) was calibrated on the same motif family the
  benchmarks use. D-065's "one robust default" claim is therefore
  in-sample.
- The floor is `N >= 750` (D-011) and `N >= 1500` for `overlap`.
  Typical cross-sectional network studies have `N = 200-500`.
- Everything is Gaussian. Most psychological data are ordinal.

A one-replicate probe run during the review, on a psych-like random
network (`p = 20`, density `.35`, `N = 300`, mostly positive edges
`.1-.3`), found:

- **71% of pairs passed the `.001` marginal screen.** The screen, which
  D-065 credits for GOPC's precision, was largely inert.
- GOPC still did reasonably: sensitivity `.59`, specificity `.96`,
  against PC@.01 at `.41 / 1.00` and EBICglasso at `.84 / .72`.
- **GOPC took 204 s, against 0.8 s for PC** (10.5 s vs 0.1 s at
  `p = 15`). The conditioning pool is the edge's whole connected
  component (`src/gopcnet/pipeline/growing_subset_dpi.py`), so when the
  screen passes most pairs the number of tests grows combinatorially.

This is anecdotal, one replicate per setting on an ad-hoc generator.
It motivates the plan; it is not evidence for any claim.

## The phases

| Phase | Document | Goal | Charters | Blocking? |
|---|---|---|---|---|
| 0 | [phase0_housekeeping.md](phase0_housekeeping.md) | Close Stage 6a (D-066). Ship a real default for `fit_gopc`. Add a reproducible Cholesky sampler. | none (engineering + decision-log entries) | Must finish before Phase 1 |
| 1 | [phase1_external_validity.md](phase1_external_validity.md) | Make GOPC scale to `p = 30`. Test whether the niche survives on psych-realistic networks against the full comparator set. | Stage 7a (scalable engine), Stage 7b (external-validity benchmark) | Stage 7b's outcome decides the paper's framing and whether Phase 2 proceeds as written |
| 2 | [phase2_small_sample.md](phase2_small_sample.md) | Lower the practical sample-size floor: principled default alphas valid at any `N`, a small-N edge-evidence reporting mode, a sample-size planner. | Stage 7c (default rules), Stage 7d (evidence tiers) | Depends on 7b |
| 3 | [phase3_ordinal.md](phase3_ordinal.md) | Ordinal / Likert data via a correlation-matrix input (Spearman or polychoric), with calibrated tests. | Stage 7e | Depends on the Phase 1 correlation-matrix primitive; can run in parallel with Phase 2 |

```
Phase 0 ──► Stage 7a ──► Stage 7b ──┬──► Stage 7c ──► Stage 7d
                                    │         (+ planner)
                                    └──► Stage 7e (ordinal)
```

### Stage naming

New charters are numbered **Stage 7a-7e**. The repository's old
outline (`outline/…technical_build_plan_v3…`, cited in
`docs/stage5a_charter.md`) used "Stage 7" and "Stage 8" for
broad-benchmarking and nonlinear-data phases of the retired MINT
roadmap. The new numbering continues the repo's own charter sequence
(`stage6a` is the last one) and does not refer to that outline. Say so
in each new charter's first paragraph so no reader conflates them.

### Decision-log numbering

The next free number is **D-066** (Stage 6a). Assign the rest
sequentially as entries are written. Do **not** pre-reserve numbers.
The phase documents refer to entries by purpose ("the defaults-API
entry"), not by number.

## Global rules for any agent executing this plan

These restate the handoff's standing conventions and add a few this
plan depends on. They override anything in a phase document that
appears to conflict.

1. **Never commit, push, open a PR, or dispatch a GitHub Actions
   workflow without an explicit instruction from the user in chat.**
   Prepare the change, run the tests, report, and wait. The one
   exception is anything the user has explicitly pre-authorized in the
   current session.
2. **Frozen mechanisms stay untouched:** `compose_screen_then_prune`,
   `growing_subset_dpi`, `compute_partial_correlation_evidence`,
   `screen_uncorrected`, `fit_pc_skeleton`, `fit_ebicglasso`, every
   `simulation/*` sampler, and every `experiments/stage*` module. New
   behavior is always a new function or module, and the old path stays
   callable and bit-identical. Changing what `fit_gopc` calls *by
   default* is allowed only after a decision-log entry authorizes it.
   Explicit-argument calls must keep reproducing archived evidence.
3. **Charter before run.** Every simulation with a claim attached gets
   `docs/stage7X_charter.md`, frozen (status line "FROZEN before
   results", SHA-256 recorded in the runner's `metadata.json`) before
   any full-scale run. Smoke runs (≤ 20 replicates per cell) are
   allowed before freezing, but only for timing, feasibility, and
   gate-checking, never for choosing thresholds by looking at outcome
   metrics. If a problem shows up after freezing, add a dated
   "Implementation-time amendment" section. Never edit the frozen text
   (see `docs/stage5i_charter.md` for the pattern).
4. **Development/validation split.** Any selection (an alpha, a rule, a
   `q`) happens on development replicates or development structure
   families only. Every reported number comes from validation. Stage 7c
   adds a stricter **held-out structure family** split. See that
   document.
5. **Every result gets a decision-log entry**, positive, negative, or
   mixed, in the existing format (see the template at the bottom of
   this file). Failed gates are reported as failed, not re-scoped after
   the fact.
6. **Archive evidence** under `evidence/stage7_*/<charter_dir>/` with a
   README row, as in `evidence/stage5_benchmarks/README.md`. Gzip any
   `raw_metrics.csv` over 50 MB (GitHub's hard limit is 100 MB per
   file).
7. **Use the Cholesky sampler** (Phase 0, step 0.4) for every new DGP.
   Never use `Generator.multivariate_normal` in new code (D-065's
   reproducibility failure).
8. **Tests.** Each new public function gets unit tests in
   `tests/unit/`. Each new runner gets a test that runs its smoke config
   end to end and a test that a sharded run equals an unsharded run
   (copy `test_stage5a_sharded_run_matches_unsharded_run`'s approach).
   Run the whole suite with `python -m pytest` before reporting any
   step as done.
9. **Python version.** `pyproject.toml` pins `>=3.11,<3.12`, and CI
   uses 3.11. If the local interpreter differs, say so in the report.
   Do not loosen the pin as a side effect.
10. **Scope guard.** Out of scope for the whole plan unless the user
    reopens it:
    - the hybrid GOPC+PC idea (`docs/future_directions.md`)
    - anything MI-based (`gopcnet.mi`)
    - the sequential engine
    - new toolkit features (centrality variants, new NCT statistics,
      plotting, community detection)
    - orientation or causal claims
    - nonlinear data
    - multilevel or time-series networks

    If a phase seems to need one of these, stop and ask.
11. **Stop-and-ask points** are marked **⛔ ASK** in the phase
    documents. At each one, report findings and wait for the user.

## Shared engineering conventions for new runners

Every new `src/gopcnet/experiments/stage7X.py` follows
`stage5i.py`'s structure exactly, so the generic
`.github/workflows/sharded_benchmark.yml` and
`scripts/aggregate_shards.py` work unchanged:

- A frozen `@dataclass` config, loaded by `load_stage7X_config(path)`
  and aliased as `load_config`.
- `COMBINATION_COLUMNS`, `expected_row_count(config)`, and
  `expected_combinations(config)` (the shard-aggregation contract; see
  the top of `scripts/aggregate_shards.py`).
- A companion `stage7X_reporting.py` exposing **both**
  `write_stage7X_report` and the alias
  `write_report = write_stage7X_report`. Stage 5i's aggregate job
  failed because this alias was missing (D-065). Add a unit test that
  imports `write_report` from the reporting module.
- Seeds come from
  `np.random.SeedSequence([master_seed, STAGE_TAG, *full_grid_indices, replicate])`.
  Indices are taken from the **full** configured grid, never from a
  shard's filtered subset. Pick a `_STAGE_TAG` not used by any existing
  module: grep `_STAGE_TAG` and use 701, 702, … for 7a, 7b, …
- `main()` accepts `--config`, `--output`, `--workers`, one
  comma-separated filter flag per shard dimension, and `--no-report`.
- `_write_evidence` writes `raw_metrics.csv`, `resolved_config.yaml`,
  and `metadata.json` (charter SHA-256, git commit, Python, platform,
  UTC timestamp, runtime).
- Raw rows keep failures: `status` / `error` columns, never dropped
  silently.
- Two configs per charter: `configs/stage7X_<name>.yaml` (full) and
  `configs/stage7X_<name>_smoke.yaml` (≤ 20 replicates).

## Decision-log entry template

Match the existing entries (e.g. D-053, D-065):

```markdown
## D-0NN: <one-line finding, stated as the result, not the question>

Date: YYYY-MM-DD

Stage: Stage 7X (<one-phrase role>), charter `docs/stage7X_charter.md`
(FROZEN before results; amendments: <none | list>)

Status: <PROCEED / REASSESS / Descriptive, no gate / Engineering convention>

Decision timing: <Predeclared before results — where the thresholds were fixed>

Question: <the charter's question, one paragraph>

Prior specification: <charter path, grid, methods, replicates, seeds>

Evidence: <GitHub Actions run link or "local run">, archived at
`evidence/...`. Files: raw_metrics.csv(.gz), report.json, resolved_config.yaml,
metadata.json, <report>.md, <figures>.

<Results table(s). Gates first, then each predeclared question.>

Decision: <what fires, per the charter's own branches>

Rationale: <why, in plain language; label anything post-hoc as post-hoc>

Consequences: <what changes in code / docs / manuscript; what does NOT change>
```
