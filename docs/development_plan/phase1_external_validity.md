# Phase 1 — Scalable engine and external validity

Read `README.md` in this folder first. Its global rules apply here.
Phase 0 must be complete: the defaults API and the Cholesky sampler
are both used below.

**Goal.** Answer the one question that decides what this project can
claim:

> On networks that look like psychological data (no pure-noise
> variables, all items inter-correlated, mixed strong and weak edges,
> `p` up to 30, `N` from 250 to 2000), does GOPC's single default still
> fix EBICglasso's precision problem without giving up too much
> sensitivity? And does it do better than the obvious non-regularized
> alternative?

Answering it at `p = 30` first requires an engine that scales.

**Two charters:**

- **Stage 7a** — an adjacency-set ("PC-stable-restricted") GOPC engine.
  Is it non-inferior to the current component-pool engine on the
  legacy shapes, and how much faster is it?
- **Stage 7b** — the external-validity benchmark.

**Estimated effort.**

- Engineering: 3–5 sessions.
- Stage 7a: one local or small CI run.
- Stage 7b: one large sharded CI run, roughly 3–10 hours of wall-clock
  depending on the replicate count fixed after the timing smoke.

**Order of work:**

1. 1.1 Correlation-matrix partial-correlation primitive
2. 1.2 PC-stable skeleton core over a correlation matrix
3. 1.3 GOPC adjacency engine (`engine="adjacency"`)
4. 1.4 Non-regularized comparator
5. 1.5 Refit edge weights
6. 1.6 Psych-realistic DGP generators
7. 1.7 Stage 7a: charter → runner → smoke → freeze → run → D-entry
8. 1.8 Stage 7b: charter → runner → timing smoke → freeze → run → D-entry
9. 1.9 Consequences routing (⛔ ASK)

---

## 1.1 Correlation-matrix partial-correlation primitive

**Why.** The frozen primitive
`gopcnet.dpi.multi_conditional.compute_partial_correlation_evidence`
residualizes raw data by OLS for every test. That costs `O(N·k²)` per
test, and the engines run many thousands of tests. A partial
correlation needs only the correlation submatrix: for the index list
`A = [i, j, *S]`, with `Q = inv(R[A][:, A])`,

```
pcor(i, j | S) = -Q[0, 1] / sqrt(Q[0, 0] * Q[1, 1])
```

For Pearson correlations this equals the residual-based value exactly
in exact arithmetic. The OLS in the frozen primitive includes an
intercept, and Pearson correlation centers the data, so they match.
Each test is then an inversion of a matrix of size at most 6 × 6,
independent of `N`.

It also gives Phase 3 its entry point: an ordinal-data correlation
matrix (Spearman or polychoric) plugs in unchanged.

**New module:** `src/gopcnet/dpi/correlation_based.py`.

```python
"""Partial-correlation tests computed from a correlation matrix and a sample
size, rather than from raw data. Numerically equivalent to
gopcnet.dpi.multi_conditional.compute_partial_correlation_evidence for Pearson
input (tested), orders of magnitude cheaper per test, and usable with any
correlation estimator (Phase 3). The frozen residual-based primitive is not
modified.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.stats import norm

from gopcnet.dpi.multi_conditional import PartialCorrelationEvidence

_CONDITION_LIMIT = 1e10  # submatrix condition number above which a test is inconclusive


def partial_correlation_from_corr(corr: np.ndarray, i: int, j: int, conditioning: Sequence[int]) -> float:
    ...


def partial_correlation_test_from_corr(
    corr: np.ndarray,
    n: int,
    i: int,
    j: int,
    conditioning: Sequence[int],
    *,
    se_scale: float = 1.0,
) -> PartialCorrelationEvidence:
    """Fisher-z test of pcor(i, j | conditioning) = 0.

    z = arctanh(r) * sqrt(n - 3 - |S|) / se_scale. se_scale = 1 is the exact
    Gaussian/Pearson case; Phase 3 calibrates se_scale for rank/polychoric input.
    Raises ValueError (treated by callers as "inconclusive", exactly like the
    frozen primitive) when degrees of freedom <= 0, indices are invalid, or the
    submatrix is numerically singular (condition number > _CONDITION_LIMIT).
    """
```

**Implementation details:**

- Validate `i != j`, the index ranges, and that `i`, `j` are not in
  `conditioning`. Use the same error messages as the frozen primitive
  where they overlap.
- With `|S| = 0`, `r = corr[i, j]` directly.
- Clip `r` to `±(1 - 1e-12)` before `arctanh`, as the frozen code does.
- Compute `cond = np.linalg.cond(sub)`. If it is not finite or exceeds
  `_CONDITION_LIMIT`, raise `ValueError`.
- `p_value = 2 * norm.sf(abs(z))`.
- Return the existing `PartialCorrelationEvidence` dataclass so callers
  are interchangeable.

**Tests** (`tests/unit/test_correlation_based.py`):

1. **Equivalence.** Use 50 random datasets (`p = 8`, `N ∈ {50, 300,
   2000}`), all pairs, and conditioning sets of sizes 0–4 drawn at
   random. `partial_correlation`, `z_statistic` and `p_value` must
   match the frozen primitive (with `corr = np.corrcoef(data,
   rowvar=False)`) to `atol=1e-10` on `r` and `rtol=1e-8` on `p`.
2. Degrees-of-freedom guard: `n - 3 - |S| <= 0` raises.
3. A singular submatrix (duplicate column in `corr`) raises
   `ValueError`.
4. `se_scale = 2` halves `z`.

## 1.2 PC-stable skeleton core over a correlation matrix

**Why.** D-065 Q4 showed that GOPC's pruning, at matched alpha, is
effectively PC's own search restricted to the screened graph. One core
function can then serve three roles:

- the PC comparator: complete start graph, level 0 upward
- the new GOPC engine: screened start graph, level 1 upward, capped at
  4
- Phase 3's ordinal variants: a different correlation matrix

This avoids three independent implementations of the same search.

**New module:** `src/gopcnet/pipeline/skeleton_core.py`.

```python
@dataclass(frozen=True)
class SkeletonResult:
    adjacency: np.ndarray                          # bool (p, p), symmetric
    max_p_value: np.ndarray                        # (p, p); for retained edges, max p over all tested sets
                                                   # (<= alpha); for removed edges, the p that removed it;
                                                   # NaN for pairs never tested
    min_abs_partial: np.ndarray                    # (p, p) signed pcor of minimum |pcor| over tested sets
                                                   # of size >= 1 (NaN if none); D-055 convention
    separating_set: dict[tuple[int, int], tuple[int, ...]]  # removed edges only
    n_tests: np.ndarray                            # (p, p) int, number of tests run per pair
    level_reached: int
    cap_reached: np.ndarray                        # (p, p) bool: retained, and larger sets existed beyond max_level


def pc_stable_skeleton(
    corr: np.ndarray,
    n: int,
    alpha: float,
    *,
    start_adjacency: np.ndarray | None = None,     # None = complete graph
    start_level: int = 0,
    max_level: int | None = None,                  # None = unbounded (canonical PC)
    se_scale: float = 1.0,
) -> SkeletonResult:
```

**Algorithm.** Follow PC-stable (Colombo & Maathuis, 2014), matching
`fit_pc_skeleton`'s existing semantics exactly: both endpoints'
neighbor sets, and neighbor sets frozen per level.

```
adjacency = start_adjacency.copy() (or complete, zero diagonal)
ell = start_level
loop:
    if max_level is not None and ell > max_level: break
    neighbors = {a: set(flatnonzero(adjacency[a]))}        # snapshot for this level
    any_testable = False
    removals = []
    for i < j with adjacency[i, j]:
        tested_here = set()                                 # avoid testing the same S twice for one pair
        removed = False
        for (a, b) in ((i, j), (j, i)):
            candidates = neighbors[a] - {b}
            if len(candidates) < ell: continue
            any_testable = True
            for S in combinations(sorted(candidates), ell):
                if S in tested_here: continue
                tested_here.add(S)
                try: ev = partial_correlation_test_from_corr(corr, n, i, j, S, se_scale=se_scale)
                except ValueError: continue                 # inconclusive, as in the frozen code
                n_tests[i, j] += 1
                update max_p_value[i, j] (running max); if ell >= 1 update min_abs_partial
                if ev.p_value > alpha:
                    removals.append((i, j, S)); removed = True; break
            if removed: break
    apply removals (both triangles); record separating_set
    if not any_testable: break
    ell += 1
set cap_reached for retained edges: max_level is not None and
    max(len(neighbors_final[i] - {j}), len(neighbors_final[j] - {i})) > max_level
mirror all (p, p) arrays to the lower triangle
```

**Notes:**

- The `tested_here` de-duplication only skips a set that was already
  tested for the same pair. It cannot change any decision. It can
  change `n_tests`, which is a diagnostic. Document it.
- Level 0 on the complete graph tests marginal correlations at `alpha`.
  For the GOPC engine, start at level 1. The screen at `screening_alpha
  ≤ dpi_alpha` already implies that level 0 would reject for every
  screened-in pair. State this in a comment. It is why `start_level=1`
  is equivalent, not an approximation.
- The frozen PC rows record `max_conditioning_set_size` as "the largest
  level with a removal". Keep `level_reached` as the last level
  entered, and document the difference.

**Tests** (`tests/unit/test_skeleton_core.py`):

1. **PC equivalence.** Use 200 seeded datasets: `p ∈ {5, 8, 12}`, `N ∈
   {100, 500}`, a mix of independent and chain-structured data.
   `pc_stable_skeleton(np.corrcoef(x, rowvar=False), n, .01).adjacency`
   must equal `fit_pc_skeleton(x, alpha=.01).adjacency`. Allow a
   mismatch only when the deciding p-value is within `1e-9` of `alpha`,
   and assert that explicitly.
2. On a chain `x1 → x2 → x3`, the separating set of `(0, 2)` is `(1,)`.
3. `max_level=1` never tests sets of size 2 (`n_tests` bound;
   `level_reached ≤ 1`).
4. `start_adjacency` with a missing edge is never re-added.
5. Symmetry of every returned matrix.

## 1.3 GOPC adjacency engine

**Why.** The current engine (`growing_subset_dpi`) draws conditioning
sets from the edge's entire connected component, fixed at the screen.
When the screen passes most pairs, which is typical of psychological
data, that means every subset of size ≤ 4 of the other `p - 2`
variables. `C(28, ≤4) ≈ 24,000` per edge at `p = 30`. The review's
probe measured 204 s per fit at `p = 20`.

PC theory says a separating set, when one exists, can be found within
the current adjacency set of one endpoint (under faithfulness), so the
adjacency pool is sufficient in principle. It tests far fewer sets,
which also means fewer chances for an underpowered test to wrongly
prune a weak true edge. The expected effect is a large speedup, recall
equal or slightly better, and precision equal or slightly lower.
Stage 7a measures this; nothing here assumes it.

**Changes to `src/gopcnet/pipeline/gopc.py`:**

1. Add a keyword argument `engine: Literal["component", "adjacency"] =
   "component"` to `fit_gopc`. The **default stays `"component"`**, the
   frozen mechanism. Switching the default needs its own decision-log
   entry after Stage 7b.
2. For `engine="adjacency"`:

   ```python
   corr = compute_pairwise_screening_evidence(data).correlation   # zero diagonal there; set diag to 1 for inversion
   corr = corr.copy(); np.fill_diagonal(corr, 1.0)
   screened = screen_uncorrected(evidence, alphas.screening_alpha)
   core = pc_stable_skeleton(corr, n, alphas.dpi_alpha, start_adjacency=screened,
                             start_level=1, max_level=max_conditioning_size)
   weights = where(core.adjacency,
                   where(isnan(core.min_abs_partial), corr, core.min_abs_partial), 0)
   ```

   This mirrors D-055's growing-order convention exactly. Sizes ≥ 1
   only; untested edges keep the marginal correlation. Read
   `compute_growing_order_weights` in `pipeline/weights.py` and confirm
   that before you write it.
3. Add an optional `diagnostics` field to `GOPCResult` (default
   `None`). For the adjacency engine, fill it with a small frozen
   dataclass `GOPCDiagnostics(max_p_value, n_tests, cap_reached,
   separating_set, screened)`. Phase 2's evidence tiers depend on
   `max_p_value` and `separating_set`. For the component engine, leave
   it `None`. The frozen engine is not touched.
4. Update the docstring to explain the difference in one paragraph and
   state that the default is unchanged pending Stage 7b.

**Tests** (additions to `tests/unit/test_gopc.py`):

1. On a 3-node chain and on `p = 4` independent data, both engines give
   the same adjacency.
2. With `max_conditioning_size=0`, the adjacency engine returns exactly
   the screened graph.
3. The adjacency engine's retained edges are a subset of the screened
   graph.
4. The weights follow the D-055 convention on a hand-built example.
5. Speed smoke: `p = 20`, `N = 300`, dense random network. The
   adjacency engine finishes in under 10 s. Mark it
   `@pytest.mark.slow` if the suite has markers; otherwise keep the
   test tiny.

## 1.4 Non-regularized comparator

**Why.** In the psychometric literature, the standard alternative to
EBICglasso with better specificity is non-regularized estimation:
full-order partial correlations, each tested, with multiple-testing
control (Williams & Rast, 2020, "Back to the basics"; Williams et al.,
2019, *MBR*; the `GGMnonreg` R package). Reviewers will ask about it
first, and the manuscript neither cites nor benchmarks it. **Verify
every citation before it enters the manuscript.**

**New module:** `src/gopcnet/comparators/nonregularized.py`.

```python
@dataclass(frozen=True)
class NonregularizedResult:
    adjacency: np.ndarray
    weights: np.ndarray         # full-order partial correlations, zero off-adjacency
    p_values: np.ndarray        # (p, p), one on the diagonal
    correction: str
    alpha: float


def fit_nonregularized_ggm(data, *, alpha: float = 0.05, correction: str = "holm") -> NonregularizedResult:
    """Full-order partial correlation network: every pair tested conditional on
    all other variables (Fisher z, df = N - p - 1), with multiple-testing control
    across the m = p(p-1)/2 pairs. correction in {"holm", "bh", "none"}."""
```

**Details:**

- Raise `ValueError` if `n <= p + 1`.
- `R = corrcoef`, `Q = inv(R)`, `pcor = -Q_ij / sqrt(Q_ii Q_jj)`,
  `z = arctanh(pcor) * sqrt(n - p - 1)`.
- For `bh`, reuse the logic of
  `gopcnet.screening.benjamini_hochberg_threshold` by building a
  `ScreeningEvidence` from the partial-correlation p-values rather than
  reimplementing it. Holm is a step-down: sort ascending, keep while
  `p_(k) ≤ α / (m − k + 1)`, stop at the first failure.
- Export from `gopcnet.comparators` and the top-level `__init__`.

**Tests:**

1. `pcor` equals `partial_correlation_from_corr` with `S` = all other
   variables.
2. Holm and BH on hand-computed p-value vectors.
3. On an independent-data null (`p = 10`, `N = 500`, 500 seeds), the
   family-wise false-positive rate of Holm is ≤ .05 + 3 SE.

## 1.5 Refit edge weights

**Why.** Growing-order weights are the minimum-magnitude partial
correlation among low-order tested sets (D-055). Psychology readers
read an edge weight as the partial correlation controlling for **all**
other variables, which is the GGM parameter. Downstream centrality,
NCT and bridge metrics inherit whatever the weights mean. The
constrained GGM maximum-likelihood fit (D-058,
`fit_gaussian_graphical_model`) already estimates exactly that
parameter given the selected edges.

**Add to `src/gopcnet/pipeline/weights.py`:**

```python
def refit_weights(data: np.ndarray, adjacency: np.ndarray) -> np.ndarray:
    """Partial correlations from the constrained-MLE GGM on `adjacency`'s support
    (gopcnet.metrics.fit.fit_gaussian_graphical_model): -K_ij / sqrt(K_ii K_jj),
    zero off-support. Requires N > p."""
```

- Do **not** change the default weight convention yet. Add
  `weights: Literal["min_subset", "refit"] = "min_subset"` to
  `fit_gopc`. Stage 7b Q6 decides whether `refit` becomes the default,
  through its own decision-log entry, as D-055 did.
- If `fit.converged` is `False`, warn and still return the result.

**Tests:**

1. On the saturated adjacency, `refit_weights` equals the full-order
   `pcor` from 1.4 to `1e-6`.
2. On an empty adjacency, it returns all zeros.
3. Support is preserved.

## 1.6 Psych-realistic DGP generators

**New module:** `src/gopcnet/generators/psych_networks.py`, in the
shipped subpackage created in Phase 0. It is shipped because Phase 2's
sample-size planner uses it. Everything samples through
`gopcnet.generators.sampling` (Phase 0). The Stage 7b runner imports
it from there. Once Stage 7b is frozen, treat this module as frozen
too: later changes add new functions or structures and never alter
existing ones, because the archived evidence depends on them.

### 1.6.1 Graph generators (native, no new dependencies)

All return a boolean symmetric `(p, p)` adjacency with a zero diagonal.

- `erdos_renyi(p, density, rng)`: each pair independently with
  probability `density`.
- `watts_strogatz(p, k, rewire, rng)`: a ring lattice with `k` nearest
  neighbors (`k` even, `k/2` per side). Rewire each lattice edge `(i,
  i+s)` with probability `rewire` to a uniformly chosen non-neighbor
  `j ≠ i`, skipping if none exists. Use `k = 4`, `rewire = .1`.
- `stochastic_block(p, n_blocks, p_within, p_between, rng)`: nodes
  assigned to blocks as evenly as possible (`np.array_split(range(p),
  n_blocks)`). Pair probabilities are `p_within` and `p_between`. Use
  `n_blocks = max(2, round(p / 5))`, `p_within = .6`, `p_between =
  .05`.
- `with_isolates(adjacency_fn, p, isolate_fraction, rng)`: build the
  graph on the first `p − round(isolate_fraction·p)` nodes, then append
  isolated nodes. Permute node order with `rng` so isolates are not
  always last. This re-creates the legacy "pure noise columns" regime
  inside the new family and makes the screen's contribution a
  manipulated factor instead of a hidden one.

### 1.6.2 Edge weights and the precision matrix

For each edge:

- Magnitude from a mixture: with probability `.7` draw
  `Uniform(.08, .20)` (weak), otherwise `Uniform(.20, .40)` (strong).
  This addresses the handoff's gap that every current shape gives
  recall `1.0` for everyone.
- Sign: negative with probability `.15`.

Put the signed weights into a symmetric matrix `W` (zero diagonal).
These are intended partial correlations.

To make it positive definite with a unit diagonal:

```
lam_max = max eigenvalue of W
c = min(1.0, 0.9 / lam_max) if lam_max > 0 else 1.0
P = c * W                                  # realized true partial correlations
K = I - P                                  # precision with unit diagonal; eig(K) = 1 - eig(P) >= 0.1
Sigma = covariance_from_precision(K)
d = sqrt(diag(Sigma)); Sigma = Sigma / outer(d, d)   # correlation scale; partial correlations unchanged
```

With `K_ii = 1`, `pcor_ij = -K_ij / sqrt(K_ii K_jj) = P_ij` exactly, so
the ground-truth weights are known without inversion error. **Record
`c` per replicate.** Dense graphs shrink more, which is a real property
of the design. Report the distribution of realized `|P|` by structure
in the Stage 7b report so nobody mistakes shrinkage for a method
effect.

### 1.6.3 Registry and seeding

```python
@dataclass(frozen=True)
class PsychTruth:
    adjacency: np.ndarray
    partial_correlations: np.ndarray   # P
    correlation: np.ndarray            # Sigma (unit diagonal)
    shrinkage: float                   # c
    structure: str
    truth_hash: str                    # sha256 of P.round(12).tobytes(), first 16 hex chars


STRUCTURES: tuple[str, ...] = (
    "random_sparse",        # ER, density .20
    "random_dense",         # ER, density .35
    "small_world",          # WS, k=4, rewire .1
    "clustered",            # SBM as above
    "random_with_isolates", # ER .20 on 75% of nodes, 25% isolated
)


def make_truth(structure: str, p: int, rng: np.random.Generator) -> PsychTruth: ...
def sample_data(truth: PsychTruth, n: int, rng: np.random.Generator) -> np.ndarray: ...
```

**Seeding rule, which makes cells paired across `N`:** the truth seed
depends on `(structure, p, replicate)` but **not on `N`**, so a given
replicate uses the same true network at every sample size. The data
seed adds `N`:

```
truth_seed = SeedSequence([master_seed, STAGE_TAG, structure_index, p_index, replicate, 0])
data_seed  = SeedSequence([master_seed, STAGE_TAG, structure_index, p_index, replicate, 1, n_index])
```

**Tests** (`tests/unit/test_psych_networks.py`):

1. Every structure at `p ∈ {10, 20, 30}` over 200 seeds: `K` is PD with
   minimum eigenvalue ≥ `0.1 − 1e-9`.
2. `P` has a zero diagonal and is symmetric.
3. `-inv(Sigma)` rescaled to partial correlations equals `P` to `1e-8`.
4. `make_truth` is deterministic.
5. The realized density of `random_sparse` at `p = 30` over 500 seeds
   is within `.20 ± .02`. Isolates have zero rows in `P`.
6. `watts_strogatz` has exactly `p·k/2` edges before rewiring and the
   same count after.
7. Sampling covariance recovery at large `N`.

---

## 1.7 Stage 7a — Scalable engine non-inferiority

### 1.7.1 Write `docs/stage7a_charter.md`

Use `docs/stage5g_charter.md` and `docs/stage5i_charter.md` as models.
Required sections: Background and objective; Design; Sharding;
Decision structure; Explicit non-goals; Required evidence;
Consequences; Resolutions of the pre-freeze questions.

**Content to put in the charter:**

- **Question.** Is `fit_gopc(engine="adjacency")` non-inferior to
  `engine="component"` in precision and recall on the five legacy
  shapes, and how does runtime scale with `p` on the new psych
  structures?
- **Part A (legacy shapes).**
  - Shapes: the Stage 5a DGPs (`gopcnet.experiments.stage5a._DGP_REGISTRY`,
    frozen samplers).
  - `N ∈ {750, 1000, 1500, 1750}`, strength `.5`, 1000 replicates per
    cell (dev `0–499`, val `500–999`).
  - Both engines use explicit `screening_alpha=.001`,
    `dpi_alpha=default_dpi_alpha(N)` and `max_conditioning_size=4`,
    fitted on the **same draw** within the run. There is no dependence
    on the archives, so the `overlap` sampler issue cannot affect the
    comparison.
  - Also fit `pc@.01` through both `fit_pc_skeleton` and
    `pc_stable_skeleton` for gate G1.
  - Seeds: fresh `_STAGE_TAG = 701`.
- **Part B (runtime).**
  - Structures: `random_sparse`, `random_dense` and `clustered` from
    1.6.
  - `p ∈ {10, 20, 30}`, `N = 500`, 50 replicates.
  - Both engines, with default alphas.
  - The component engine gets a per-fit wall-clock budget of 120 s:
    run it in a subprocess or check `time.perf_counter()` between
    edges and abort. Record `status="timeout"`, which counts as
    "infeasible", not "error".
- **Gates:**
  - **G1:** `pc_stable_skeleton` equals `fit_pc_skeleton` adjacency on
    ≥ 99.9% of Part A rows, all shapes.
  - **G2:** the correlation-based primitive's equivalence tests (1.1)
    pass in CI at the run's commit. Record the commit.
- **Q1 (non-inferiority).** Per `(shape, N)` cell, on validation
  replicates:
  - paired `precision_adj − precision_comp` and
    `recall_adj − recall_comp`, each with a 95% bootstrap CI (2,000
    resamples of replicate indices)
  - **Non-inferior** if the lower CI bound is ≥ `−.02` for both
    metrics. `.02` is Stage 5g's recall tolerance.
  - Verdict per shape: NON-INFERIOR if all 4 cells pass; MIXED if 2–3
    pass; INFERIOR if 0–1 pass.
- **Q2 (agreement).** Mean symmetric edge difference per replicate
  between the engines, compared with a same-engine noise floor. Use the
  D-065 Q4 method: refit at `alpha × 1.25` to estimate the floor.
  Descriptive.
- **Q3 (runtime).** Median and 90th-percentile seconds per fit per
  `(structure, p)` for each engine, plus the fraction of component-engine
  fits that time out. Descriptive.
- **Consequences, predeclared:**
  - If G1 and G2 pass and Q1 is NON-INFERIOR on all five shapes:
    Stage 7b uses `engine="adjacency"` as "GOPC". The component engine
    is included in 7b only at `p = 10`, as a bridge.
  - If Q1 is MIXED or INFERIOR on any shape: **⛔ ASK**. The options
    are (a) run 7b with the component engine at `p ≤ 20` only, or
    (b) investigate first.
  - In either case, **the `fit_gopc` default engine does not change as
    a consequence of 7a alone.**

### 1.7.2 Implement `src/gopcnet/experiments/stage7a.py` and `stage7a_reporting.py`

Follow the shared runner conventions in `README.md`.

- Row schema (one row per replicate × method):

  ```
  part, dgp_or_structure, p, n, method, replicate, seed, truth_hash,
  precision, recall, f1, shd, n_estimated_edges, edge_bits,
  n_tests_total, elapsed_seconds, status, error
  ```

  - `method ∈ {gopc_component, gopc_adjacency, pc_frozen, pc_core}`
  - Reuse `stage5a._graph_metrics` for scoring and `stage5i.encode_edges`
    for `edge_bits`. Import them; do not copy.
- Shard dimensions: `--parts A,B`, `--dgps …`, `--sample-sizes …`.
  Part B has one `N` and its own structure list. Make the runner's
  cell enumeration and `expected_combinations` agree exactly. **Shards
  whose filters select no cells must write an empty `raw_metrics.csv`
  with the header row and exit 0, not raise.** Stage 5i raised
  `ValueError("… selected no cells")`, which fails the job.
- Reporting: `write_stage7a_report(raw, config, output_dir)` and the
  alias `write_report`. Write `report.json`, `stage7a_report.md`, a
  runtime-vs-`p` figure (log y-axis), and a per-shape
  non-inferiority forest plot.
- Configs: `configs/stage7a_engine.yaml` and
  `configs/stage7a_engine_smoke.yaml` (10 replicates, Part B 3
  replicates).
- Tests (`tests/unit/test_stage7a.py`):
  - the smoke config runs end to end in a temp dir
  - sharded equals unsharded on a 2-cell subset
  - `expected_row_count` matches the smoke output
  - `write_report` is importable
  - an empty-shard run writes a header-only CSV

### 1.7.3 Run

1. `python -m gopcnet.experiments.stage7a --config configs/stage7a_engine_smoke.yaml --output <scratchpad>/stage7a_smoke`.
   Check gates G1 and G2 and the timings. Do not look at Q1 outcomes to
   tune anything.
2. Freeze the charter. Set the status line and date, and record its
   SHA-256 in the runner's metadata automatically, as in `stage5i.py`.
3. Part A at 1000 replicates is cheap for the adjacency engine but not
   for the component engine at `p = 15` (about 0.01–0.1 s per fit on
   the legacy shapes, per D-047). A local run is probably fine. Estimate
   from the smoke run. If it is over 2 hours locally, **⛔ ASK** to
   dispatch `sharded_benchmark.yml` with
   `runner_module=gopcnet.experiments.stage7a`, `dim1_flag=--dgps`, and
   so on.
4. Archive under `evidence/stage7_scalable_engine/stage7a_engine/`,
   write the D-entry, and **⛔ ASK** before committing.

---

## 1.8 Stage 7b — External-validity benchmark

### 1.8.1 Write `docs/stage7b_charter.md`

This is the most important charter in the plan. The central
predeclared question is whether GOPC's advantage over EBICglasso
survives on psych-realistic networks, and how it compares with
non-regularized testing.

**Design grid:**

| Factor | Levels |
|---|---|
| Structure | `random_sparse`, `random_dense`, `small_world`, `clustered`, `random_with_isolates` (from 1.6) |
| `p` | 10, 20, 30 |
| `N` | 250, 500, 1000, 2000 |
| Replicates | Set by the timing rule below, target 500. Truth drawn per replicate, paired across `N`. |

That gives 60 cells. Add the **anchor**: `legacy_chain_fork_hub`
(frozen Stage 5a sampler, strength `.5`, `p = 15` only) at `N ∈ {1000,
1500}`. That is 2 more cells, used only for gate G3.

**Methods, all fitted on the same draw:**

| Label | Call |
|---|---|
| `gopc` | `fit_gopc(data, engine=<7a outcome>)`, **default alphas** (Phase 0). At `N ∈ {250, 500}`, `default_dpi_alpha` is extrapolated (≈ .21 and .17); that is the point, so record the warning and don't suppress the cell. |
| `gopc_component` | `p = 10` only; bridge to the frozen engine |
| `pc@{.001,.005,.01,.05}` | `pc_stable_skeleton(corr, n, α)` |
| `ebicglasso` | `fit_ebicglasso(data)`, `γ = .5` (qgraph default; frozen) |
| `nonreg_holm` | `fit_nonregularized_ggm(data, alpha=.05, correction="holm")` |
| `nonreg_bh` | `fit_nonregularized_ggm(data, alpha=.05, correction="bh")` |

**Metrics per (replicate, method):**

- Structure: sensitivity (= recall), specificity, precision, F1, MCC,
  `n_estimated_edges`, SHD.
  `MCC = (TP·TN − FP·FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))`; NaN if
  the denominator is 0.
- **Weights, native:** Pearson correlation and MAE between the
  method's native weight vector and the true `P` over all `p(p−1)/2`
  pairs.
  - GOPC: min-subset weights.
  - EBICglasso: its shrunken partial correlations.
  - Non-regularized: full-order weights.
  - PC has no native weights: NaN.
- **Weights, refit:** the same two metrics after
  `refit_weights(data, adjacency)`, for every method. This compares
  structure quality on a common weight scale.
- **Centrality:** Spearman correlation between estimated and true node
  strength (`Σ_j |w_ij|`), using refit weights. NaN if either vector is
  constant.
- **GOPC mechanism diagnostics** (the `gopc` method only):
  - `screen_pass_fraction`: screened pairs / all pairs
  - `null_removed_by_screen`: true non-edges excluded by the screen /
    all true non-edges
  - `null_removed_by_prune`: true non-edges screened in but pruned / all
    true non-edges
  - `true_edges_lost_at_screen` and `true_edges_lost_at_prune`
  - total `n_tests`
  - `cap_reached` count
- Runtime: `elapsed_seconds`.
- Truth descriptors per row: `truth_hash`, `shrinkage_c`, `true_n_edges`,
  and the mean `|P|` over true edges.

**Replicate-count rule (predeclare it; this is the only thing the
timing smoke is allowed to set):**

1. Run the smoke at 5 replicates per cell, all methods, on the
   GitHub-hosted runner type if possible. Otherwise run locally and
   scale by a factor measured from a single known CI shard, e.g.
   Stage 5i's.
2. Let `t_cell` = the projected seconds per replicate for the slowest
   cell (expected: `ebicglasso` at `p = 30`, about 20–40 s).
3. `R = min(500, floor(4.0 h × 3600 / t_cell))`, rounded down to a
   multiple of 50, with a floor of 200. If `R < 200` would be needed,
   **⛔ ASK**.
4. Record `R` in an implementation-time amendment before the full run.
   Dev = the first `R/2` replicates, validation = the rest.

**Gates (pipeline integrity; if any fails, stop):**

- **G1:** `pc_stable_skeleton` equals `fit_pc_skeleton` on ≥ 99.9% of
  rows, for a 30-replicate subsample per cell at `p ≤ 20`, computed
  in-run (add a hidden method `pc_frozen@.01` on those replicates
  only).
- **G2:** the truth is paired across `N`. For every `(structure, p,
  replicate)`, `truth_hash` is identical across all `N`. Every truth
  satisfies the PD margin.
- **G3:** anchor continuity. On `legacy_chain_fork_hub`, GOPC with the
  **component** engine and explicit `(.001, default_dpi_alpha(N))`
  must match the archived Stage 5g cell means for precision and
  recall at `N ∈ {1000, 1500}`, with unpaired `|z| ≤ 3`. Archive:
  `evidence/stage5_benchmarks/stage5g_growing_subset/raw_metrics.csv`,
  rows with `dgp == "chain_fork_hub"` and
  `method == "gopc_growing_subset"`. That file's `alpha` column holds
  the D-012 value per `N`; assert that it equals
  `default_dpi_alpha(N)`. This confirms the new runner reproduces the
  old pipeline's behavior.

**Descriptive questions, with predeclared readings.**

All questions use validation replicates. Cell verdicts are counted
within each structure, never pooled across structures. Every paired
comparison reports the mean paired difference and a 95% bootstrap CI
(2,000 resamples of replicate indices). `N = 250` cells are always
reported separately, labeled "below every validated range;
characterization only", and excluded from the HOLDS/PARTIAL/FAILS
counts, which use the 9 cells per structure with `N ≥ 500`.

- **Q1 — Does EBICglasso's weakness exist in these regimes?**
  - Report EBICglasso's precision and specificity versus `N`, per
    structure and `p`.
  - Classify the trend as increasing, flat or decreasing, using the
    D-050 method.
  - Predeclared expectation, from the literature on EBICglasso's
    specificity at larger `N`: precision does not approach 1 as `N`
    grows.
  - If EBICglasso's precision is already ≥ .95 in most cells, **the
    problem GOPC fixes is not present in realistic regimes**. Say so
    plainly.
- **Q2 — Primary niche claim (GOPC vs EBICglasso).** A cell "supports
  the niche" if both hold:
  - (i) the paired `precision_gopc − precision_ebic` has a CI entirely
    above `.05`
  - (ii) the paired `F1_gopc − F1_ebic` has a CI lower bound ≥ `−.02`

  Per structure: **HOLDS** if ≥ 7 of 9 cells support it, **PARTIAL** if
  3–6 do, **FAILS** if ≤ 2 do.
- **Q3 — GOPC vs non-regularized testing.** Per cell, compare
  `MCC_gopc` against each of `nonreg_holm` and `nonreg_bh`:
  - "better": the CI is entirely above `.01`
  - "worse": the CI is entirely below `−.01`
  - "comparable": otherwise

  Report counts per structure. Also report sensitivity and specificity
  separately. The two approaches may trade off differently: Holm's
  family-wise control is very conservative at small `N` and large `p`,
  as seen in the review's probe (sensitivity .19).
- **Q4 — One default vs one PC alpha (replicates D-065 Q3 out of
  sample).**
  - On dev replicates, for each `N`, select the single PC alpha from
    `{.001, .005, .01, .05}` with the highest mean MCC across all
    structures and `p`, with equal weights per `(structure, p)`.
  - On validation, count cells where `pc@selected` is comparable or
    better than GOPC (MCC CI lower bound ≥ `−.01`).
  - Also count the reverse.
  - Report whether any **single** PC alpha is comparable or better
    across all 15 `(structure, p)` combinations at a given `N`.
  - Predeclared reading: D-065's "GOPC's one default covers regimes PC
    needs per-dataset tuning for" **replicates** if, at ≥ 3 of the 4
    `N`, no single PC alpha is comparable or better in every
    combination while GOPC is comparable or better than `pc@selected`
    in ≥ 80% of cells. Otherwise it does not replicate.
- **Q5 — Does the mechanism transfer?** Report the mean
  `null_removed_by_screen` and `null_removed_by_prune` per structure,
  `p` and `N`.
  - Predeclared prediction from the review: in the four structures
    without isolates, at `N ≥ 1000`, the screen removes **< 50%** of
    true non-edges, so precision comes mainly from pruning.
  - In `random_with_isolates` the screen's share is materially larger.
  - Report whether each part holds.
- **Q6 — Weight convention.** For GOPC, compare the native
  (min-subset) and refit weight MAE against the true `P`, per cell.
  Predeclared: recommend `refit` as the new default if refit MAE is
  lower (CI entirely below 0) in ≥ 75% of validation cells with `N ≥
  500`. The switch still needs its own decision-log entry (a D-055
  successor).
- **Q7 — Runtime.** Median and 90th-percentile seconds per method,
  `p` and `N`. Descriptive. This corrects the D-047 "orders of
  magnitude faster" claim to its actual scope.

**Consequences, predeclared routing (put this table in the charter):**

| Outcome | Condition | Consequence |
|---|---|---|
| **A: niche confirmed** | Q2 HOLDS in ≥ 3 of the 4 non-isolate structures, and Q3 is not "worse" in a majority of cells for both non-regularized variants | Paper keeps the D-065 framing, now with external validity. Proceed to Phase 2 as written. Consider switching the `fit_gopc` default engine to `adjacency` (own D-entry). |
| **B: noise-variable niche only** | Q2 HOLDS or is PARTIAL in `random_with_isolates` but FAILS in most non-isolate structures | Restate the contribution: GOPC helps when the variable set includes irrelevant or weakly connected variables (e.g. broad item pools, exploratory batteries). **⛔ ASK** before Phase 2; Phase 2's rules may then be scoped to that use case. |
| **C: non-regularized dominates** | Q3 "worse" in a majority of cells for either non-regularized variant, across ≥ 3 structures | EBICglasso's weakness is fixed by non-regularized testing in general. GOPC's remaining distinct value, if any, would be small-`N` behavior (where Holm/BH lose power) or speed. **⛔ ASK**: the paper's thesis changes. |
| **D: niche fails** | Q2 FAILS in ≥ 3 structures, including `random_with_isolates` | **⛔ ASK.** Stop feature work. Report as a scoping result. |
| Mixed / other | anything else | Report per the charter's own branches. **⛔ ASK.** |

**Explicit non-goals:**

- no ordinal data (Phase 3)
- no new alpha rules (Phase 2)
- no tuning of any method's settings on 7b data, except Q4's
  predeclared dev-set PC-alpha selection
- no empirical-data-derived truths (optional extension, 1.8.5)
- no claims below `N = 500`

### 1.8.2 Implement `src/gopcnet/experiments/stage7b.py` and `stage7b_reporting.py`

- `_STAGE_TAG = 702`.
- Config fields:

  ```
  structures, ps, sample_sizes, replicates, master_seed,
  development_replicates, validation_replicates, pc_alphas,
  nonreg_alpha, ebicglasso_gamma, gopc_engine,
  anchor_sample_sizes, g1_subsample_replicates
  ```

- Cell enumeration:
  - `(structure, p, N)` for the 5 structures × 3 `p` × 4 `N`
  - plus `("legacy_chain_fork_hub", 15, N)` for the anchor sample sizes
- Shard dimensions: `--structures`, `--ps`, `--sample-sizes`, for the
  three-dimension workflow mode. Anchor cells come up when
  `--structures` includes `legacy_chain_fork_hub` **and** `--ps`
  includes 15 **and** `--sample-sizes` includes an anchor `N`. Every
  other combination for that structure yields an empty shard. Empty
  shards write a header-only CSV and exit 0 (see 1.7.2).
- Anchor seeds: use Stage 5a's `_condition_seed` with Stage 5a's
  `dgp_index` for `chain_fork_hub` and its full `N` grid index. The
  draws then equal the archived ones (chain_fork_hub is not the
  degenerate-SVD case) and G3 can also be checked row-wise, as a bonus
  report, not a gate.
- Per replicate:
  1. Generate the truth from the truth seed, and data from the data
     seed.
  2. Compute the correlation matrix **once** and share it across
     `gopc` (adjacency engine), `pc@*` and the diagnostics.
  3. Fit each method in a `try` block, recording `status`/`error`.
     Time each fit separately.
- Weight metrics are computed inside the runner. Raw rows then need
  only scalars. Do **not** store weight matrices; `edge_bits` is enough
  for adjacency.
- Reporting module:
  - `write_stage7b_report` and the `write_report` alias
  - `report.json` with every gate and question verdict, machine-readable
  - `stage7b_report.md` with the full tables per question, per
    structure, and the `N = 250` section
  - figures:
    - (a) precision vs `N` per method, faceted by structure × `p`
    - (b) sensitivity vs specificity scatter per method and cell
    - (c) the screen/prune null-removal shares (Q5)
    - (d) runtime vs `p` (log)
    - (e) the realized true-weight distribution by structure
  - The development-set PC-alpha selection (Q4) is computed from dev
    replicates **inside** the reporting module. Assert that no
    validation replicate enters it.
- Configs: `configs/stage7b_external_validity.yaml` (full) and
  `configs/stage7b_external_validity_smoke.yaml` (5 replicates;
  `g1_subsample_replicates: 5`).
- Tests (`tests/unit/test_stage7b.py`):
  - the smoke config runs end to end on a reduced grid (1 structure, `p
    = 10`, 2 `N`)
  - sharded equals unsharded
  - truth paired across `N`
  - empty shard
  - the reporting functions on a synthetic `raw` frame with known
    answers (e.g. fabricate rows where GOPC precision exceeds EBIC's by
    exactly .1 and check the Q2 classification)
  - `write_report` alias present

### 1.8.3 Run

1. Smoke locally. Check that the gates compute, and check the
   timings. Apply the replicate-count rule and write the amendment.
2. Freeze the charter.
3. **⛔ ASK** to dispatch
   `.github/workflows/sharded_benchmark.yml` with:
   - `runner_module=gopcnet.experiments.stage7b`
   - `config=configs/stage7b_external_validity.yaml`
   - `dim1_flag=--structures`, with `dim1_values` set to all six,
     including the anchor
   - `dim2_flag=--ps`, `dim2_values=10,15,20,30`. `15` exists only for
     the anchor; the others are empty shards.
   - `dim3_flag=--sample-sizes`, `dim3_values=250,500,1000,1500,2000`
     (`1500` is anchor-only)

   That is 6 × 4 × 5 = 120 shards, many of them empty. If that is
   wasteful, run the anchor as a separate local job and dispatch only
   the 60 main cells. Decide at freeze and write the decision into the
   charter.
4. If the aggregate job fails, download the shards (with permission)
   and run `scripts/aggregate_shards.py` locally, as in Stage 5i.
5. Archive under `evidence/stage7_external_validity/stage7b_benchmark/`.
6. Write the D-entry with all gates, Q1–Q7, and the predeclared routing
   outcome (A/B/C/D/mixed).

### 1.8.4 Update the standing documents

- `docs/validated_operating_ranges.md`: a new section, "External
  validity (Stage 7b)", with the per-structure verdicts and the
  corrected runtime statement. Scope every claim to `p ≤ 30`, Gaussian
  data, these five structure families, and `N ≥ 500` (`N = 250`
  characterization only).
- If Q6 recommends `refit`: a separate D-entry, "Weight convention
  v2", then change `fit_gopc`'s `weights` default. Update the
  CHANGELOG as a **breaking behavior change** and add a regression test
  pinning the old behavior under `weights="min_subset"`.
- If outcome A: a separate D-entry to make `engine="adjacency"` the
  default. Mark it breaking in the CHANGELOG. Explicit
  `engine="component"` still reproduces all archived results.

### 1.8.5 Optional extension (only if the user asks): empirical-derived truths

Isvoranu & Epskamp (2021) derive true networks from networks estimated
on real datasets. That adds realism, but it needs a real dataset and
its license. If the user wants it:

- **⛔ ASK** which dataset. Candidates are public psychological item
  datasets; check each license.
- Estimate a network once with `fit_nonregularized_ggm` at `N`-full,
  sparsified at `|pcor| > .05`, and treat it as a fixed truth.
- Add it as a sixth structure in a follow-up charter (Stage 7b-2),
  never by amending 7b.

## 1.9 Consequences routing

After the Stage 7b D-entry is written, **⛔ ASK** the user with a
one-paragraph summary:

- the outcome letter
- the Q2 and Q3 tables
- what the routing table says to do next

Do not start Phase 2 until the user confirms the direction.

**Manuscript.** `manuscript/` is local only and never committed. If
the user asks for manuscript updates:

- add Stage 7b as a new Results subsection
- revise Section 6.4 (scope limitations): the "real data" and "noise
  manipulation" gaps become partly addressed
- revise the runtime claims everywhere
- add the non-regularized comparator to Section 2 (related work) and
  Section 3.3 (comparators)
