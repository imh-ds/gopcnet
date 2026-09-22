# Phase 3 — Ordinal (Likert-type) data

Read `README.md` in this folder first. Its global rules apply here.

**Prerequisites:**

- From Phase 1: the correlation-matrix primitive (1.1), the PC-stable
  core (1.2), the adjacency engine (1.3), the non-regularized
  comparator (1.4), and the psych generators (1.6).
- Stage 7b's D-entry written, and the user's go-ahead after the Phase 1
  routing.
- Phase 3 can run in parallel with Phase 2. It does not depend on
  Stage 7c or 7d. If Stage 7c adopted defaults v2 before Stage 7e is
  frozen, the charter must state which defaults version it uses.

**Goal.** Close the most obvious gap a psychology reviewer will raise:
every result so far is Gaussian, while most psychological data are
ordinal. Do it **without a new estimator**. GOPC's tests only need a
correlation matrix and an effective sample size, so ordinal support
means:

1. a correlation estimator suited to ordinal data (Spearman-based or
   polychoric)
2. a check that the Fisher-z tests stay calibrated on that input
3. a benchmark against the field's own ordinal default, EBICglasso on
   polychoric correlations (qgraph's `cor_auto` convention)

**Explicitly out of scope:**

- binary data (the Ising model is a different model family)
- nominal data
- mixed continuous and ordinal data (a later charter could add it)
- missing-data handling
- the component engine: ordinal input is supported only with
  `engine="adjacency"`

**Estimated effort.**

- Engineering: 3–4 sessions. The polychoric estimator is the main
  work.
- Stage 7e: one sharded CI run.

**Background the agent must know:**

- **Pearson on ordinal data** is biased towards zero relative to the
  latent correlation. Worse for conditional-independence testing: a
  **categorized mediator does not fully block** a path. If `X – M – Y`
  holds on the latent scale, the partial correlation of observed `X`
  and `Y` given observed `M` is not zero, so the test's false-rejection
  rate **grows with `N`**. No choice of alpha fixes a bias that grows
  with `N`. This is the core reason ordinal support must be tested, not
  assumed.
- **Polychoric correlation** estimates the latent Gaussian correlation
  under a thresholded-normal model. It removes that bias when the model
  holds, but it is noisier than Pearson. The Fisher-z standard error
  `1/sqrt(N − |S| − 3)` is then too small, so tests are anti-conservative
  unless `se_scale > 1`.
- **Rank correlations with a sine transform** (the nonparanormal
  approach; Liu et al., 2012; Harris & Drton, 2013, for PC with rank
  correlations) are consistent for continuous monotone transformations
  of a Gaussian. With few categories and heavy ties they are biased,
  though less than raw Pearson.
- Verify every citation before it enters the manuscript.

---

## 3.1 Correlation estimators (`src/gopcnet/correlation.py`, shipped)

```python
@dataclass(frozen=True)
class CorrelationEstimate:
    matrix: np.ndarray        # (p, p), unit diagonal, symmetric, positive definite (after repair)
    method: str               # "pearson" | "spearman" | "polychoric"
    n: int                    # rows used
    repaired: bool            # True if a PD repair was applied
    max_repair_change: float  # max |change| from repair (0.0 if none)
    failures: tuple[tuple[int, int], ...]  # pairs whose estimation failed and fell back (see below)


def estimate_correlation(data: np.ndarray, method: str = "pearson") -> CorrelationEstimate: ...
def is_ordinal_like(data: np.ndarray, *, max_categories: int = 7) -> np.ndarray:
    """Per-column bool: integer-valued with <= max_categories distinct values."""
```

### 3.1.1 Pearson

`np.corrcoef(data, rowvar=False)`, validated with the same checks
`gopcnet.screening.pairwise_correlation._validate_data` uses. Reuse
that function; don't copy it.

### 3.1.2 Spearman with sine transform

- `rho_s = scipy.stats.spearmanr(data).correlation`, with average ranks
  for ties. Special case `p = 2`: `spearmanr` returns a scalar, so
  build the 2 × 2 matrix yourself.
- `R = 2 * sin(pi * rho_s / 6)`, with the diagonal set to 1.
- PD repair (3.1.4) if needed.

### 3.1.3 Polychoric (two-step maximum likelihood)

For each column:

- The observed categories are its sorted unique values, relabeled to
  `0..K-1`.
- Thresholds are `τ_k = Φ⁻¹(cumulative proportion up to category k)`
  for `k = 0..K-2`, padded with `−∞` and `+∞`.
- Columns with `K < 2` are an error, as for zero variance.

For each pair `(a, b)`:

1. Build the `K_a × K_b` contingency table `n_ij`.
2. Cell probability under latent correlation `ρ`:

   ```
   π_ij(ρ) = Φ2(τa_{i+1}, τb_{j+1}; ρ) − Φ2(τa_i, τb_{j+1}; ρ) − Φ2(τa_{i+1}, τb_j; ρ) + Φ2(τa_i, τb_j; ρ)
   ```

3. Maximize `ℓ(ρ) = Σ n_ij log max(π_ij(ρ), 1e-300)` over `ρ ∈ [−.999,
   .999]` with `scipy.optimize.minimize_scalar(method="bounded")`.
   Thresholds stay fixed (two-step).
4. If the optimizer fails or returns non-finite: fall back to the
   Spearman-sine value for that pair, record the pair in `failures`,
   and continue. Never raise mid-matrix.

**Bivariate normal CDF `Φ2(h, k; ρ)`.** This is the performance-critical
piece. It must be vectorized over all threshold pairs for one `ρ`.

- **Reference implementation** (tests only):
  `scipy.stats.multivariate_normal(mean=[0, 0], cov=[[1, ρ], [ρ, 1]]).cdf(np.column_stack([h, k]))`.
- **Production implementation:** Owen's T function
  (`scipy.special.owens_t`, vectorized), using the standard identity
  for finite `h`, `k` with `h ≠ 0`, `k ≠ 0`:

  ```
  Φ2(h, k; ρ) = ½Φ(h) + ½Φ(k) − T(h, a_h) − T(k, a_k) − β
  a_h = (k − ρh) / (h·sqrt(1 − ρ²)),   a_k = (h − ρk) / (k·sqrt(1 − ρ²))
  β = 0 if h·k > 0, or (h·k = 0 and h + k ≥ 0); otherwise ½
  ```

  Handle these as explicit special cases before applying the identity:
  - `h = −∞` or `k = −∞` gives 0
  - `h = +∞` gives `Φ(k)`, and `k = +∞` gives `Φ(h)`
  - `h = 0` or `k = 0`: nudge by `±1e-12`, which is simplest and
    accurate enough, or use the limit form

  **The test in 3.1.6 is the authority.** If the identity's sign
  conventions give any disagreement with the reference beyond `1e-7`,
  fix the implementation. Do not loosen the tolerance. If Owen's T
  cannot be made to agree, fall back to the vectorized scipy reference
  and accept the slower speed. **⛔ ASK** only if the full estimator at
  `p = 20`, `N = 1000`, `K = 5` then takes more than 10 s.
- **Zero cells:** no continuity correction by default (`zero_add=0.0`
  parameter). Record the choice in the defaults decision entry. Stage
  7e reports how often zero cells occur.

### 3.1.4 Positive-definite repair (all methods)

If `min eigenvalue < 1e-6`:

- eigen-decompose
- clip the eigenvalues at `1e-4`
- reconstruct the matrix
- rescale to a unit diagonal
- set `repaired=True` and record `max_repair_change`

This is a simple Higham-style one-step projection. Document that it is
not the full alternating-projections nearest correlation matrix.

### 3.1.5 Wiring into the estimators (additive)

- **`fit_gopc`:**
  - Add `correlation: Literal["pearson", "spearman", "polychoric",
    "auto"] = "pearson"` and `se_scale: float | None = None`.
  - Any value other than `"pearson"` requires `engine="adjacency"`;
    otherwise raise `ValueError` with a clear message.
  - `se_scale=None` means "use the calibrated default for this method"
    from `gopcnet.defaults`, which Stage 7e sets. Until then it is
    `1.0`, with an `OutsideValidatedRangeWarning` for non-Pearson
    input.
  - `"auto"` uses polychoric if every column is ordinal-like, else
    Pearson if none is. **Mixed columns raise** `ValueError` pointing
    to the scope note. Implement `"auto"` only if Stage 7e's
    consequences authorize it; until then, raise
    `NotImplementedError`.
- **Screening from a correlation matrix.** Add
  `screening_evidence_from_correlation(corr, n, se_scale=1.0) ->
  ScreeningEvidence` in `gopcnet/screening/pairwise_correlation.py` as
  a new function. The z-statistic is `arctanh(r)·sqrt(n − 3)/se_scale`.
  With Pearson input and `se_scale = 1` it must equal
  `compute_pairwise_screening_evidence` (test to `1e-12`).
- **Pruning:** `pc_stable_skeleton(corr, n, alpha, ..., se_scale=...)`,
  which already exists from 1.2.
- **Comparators from a correlation matrix**, as new functions next to
  the frozen ones:
  - `fit_ebicglasso_from_correlation(corr, n, *, gamma=.5, ...)`: the
    same lambda path and EBIC as `fit_ebicglasso`, with the given
    matrix in place of `np.cov(data)`. Test that passing
    `np.cov(data)` reproduces `fit_ebicglasso(data)` exactly. Note: the
    frozen function uses the covariance; qgraph uses the correlation
    matrix. The new function takes whatever matrix it is given. Stage
    7e passes correlation matrices for every input type, for
    comparability.
  - `fit_nonregularized_ggm_from_correlation(corr, n, *, alpha,
    correction, se_scale=1.0)`.
  - The PC comparator is `pc_stable_skeleton(corr, n, α)` directly.
- **`GOPCResult`** records `correlation_method` and `se_scale`, as new
  trailing fields with defaults.

### 3.1.6 Tests (`tests/unit/test_correlation.py`)

1. `Φ2` production vs reference: on a grid of `h, k ∈ {−3, −1, −.2, 0,
   .2, 1, 3, ±inf}` and `ρ ∈ {−.95, −.5, 0, .3, .8, .95}`, max
   absolute difference ≤ `1e-7`.
2. **Polychoric recovery:** latent bivariate normal with `ρ ∈ {0, .3,
   .6}`, `N = 20,000`, thresholds for `K = 5` (symmetric and skewed).
   The estimate is within `.02` of `ρ`.
3. Polychoric on continuous-looking data with many categories
   (`K = 7`, `N` large) is close to Pearson on the latent data.
4. Spearman-sine on continuous Gaussian data recovers `ρ` within `.02`
   at `N = 20,000`.
5. PD repair: a constructed non-PD "correlation" matrix is repaired,
   has a unit diagonal, is PD, and has `repaired=True`.
6. A fallback path: force optimizer failure (monkeypatch) and check
   that `failures` is recorded and the Spearman value is used.
7. `is_ordinal_like` on integer data vs float data.
8. `fit_gopc(correlation="spearman")` with the component engine raises.
9. Timing: `p = 20`, `N = 1000`, `K = 5` polychoric in under 10 s
   (slow marker).

---

## 3.2 Ordinal data generation (`gopcnet/generators/ordinal.py`, shipped)

```python
def ordinalize(latent: np.ndarray, *, categories: int, skew: str, rng: np.random.Generator | None = None) -> np.ndarray:
    """Cut each latent standard-normal column into `categories` ordered
    integer categories 0..K-1 using fixed thresholds:
      skew="symmetric": τ_k = Φ⁻¹(k / K), k = 1..K-1 (equal-probability categories)
      skew="floor":     τ_k = Φ⁻¹(k / K) + 1.0 (most mass in low categories; symptom-scale floor effect)
    The same thresholds apply to every column (deterministic; rng unused, kept for API symmetry)."""
```

The latent data come from Stage 7b's truths
(`gopcnet.generators.psych_networks`), so the ground truth is the
latent partial-correlation network, the estimand a polychoric-based
method targets.

**Tests:**

1. The category proportions for "symmetric" are ≈ `1/K` each at large
   `N`.
2. "floor" puts more than 50% of the mass in category 0 for `K = 5`.
   Check the actual number and state it in the docstring.
3. The output is integer, in `0..K−1`.

---

## 3.3 Stage 7e charter (`docs/stage7e_charter.md`)

Two parts. **Part A** (test calibration) decides the `se_scale`
defaults. **Part B** (recovery benchmark) uses them. Both parts are
frozen in one charter, but Part A's selection is applied on Part A's
own data before Part B's metrics are looked at. The runner computes
Part A's selection first and writes it into Part B's resolved config
automatically, so no human choice sits between them.

### 3.3.1 Part A — Null calibration of the pruning test

**DGP ("k-mediator motif").**

- Latent variables `X`, `Y`, and mediators `M1..Mk`, with `k ∈ {1, 2,
  4}`.
- Edges: `X–Mi` and `Y–Mi` for every `i`, with partial correlation
  `.3`. There is **no** `X–Y` edge. Build the precision matrix as in
  1.6.2, with PD scaling.
- On the latent scale, `X ⟂ Y | {M1..Mk}` exactly.
- Ordinalize all variables with `K ∈ {3, 5, 7}` and skew ∈
  {symmetric, floor}.

**Test under evaluation.** The partial-correlation test of `(X, Y)`
given the true mediator set, computed with
`partial_correlation_test_from_corr` on each correlation estimate.

**Factors:**

- correlation ∈ {pearson, spearman, polychoric}
- `se_scale` ∈ {1.0, 1.1, 1.2, 1.35, 1.5}
- nominal α ∈ {.01, .05, .10}
- `N ∈ {250, 500, 1000, 2000}`
- `R = 2000` replicates per `(k, K, skew, N)`

The test is cheap. The correlation estimate is computed once per
replicate and reused across `se_scale` and α.

**Metric.** The empirical rejection rate. The latent null is true, so
this is the type-I error rate. Report its binomial 95% CI.

**Seeds:** `_STAGE_TAG = 705`. Dev replicates are the first half,
validation the second half.

**Selection rule** (predeclared; dev replicates; per correlation
method):

- Choose the **smallest** `se_scale` such that, at α = .05, the
  empirical rate is ≤ .075 (1.5 × nominal) in ≥ 90% of dev cells with
  `N ≥ 500`.
- A single `se_scale` is chosen per method, not per `K`, to keep the
  default simple.
- If none qualifies, the method is **not calibrated**. Record that, and
  Part B still runs it at `se_scale = 1.0` for descriptive comparison
  only.

**Predeclared expectations** (report whether each holds):

- (i) Pearson's rejection rate **increases with `N`** at fixed `K`,
  because of the mediator-blocking failure. No `se_scale` qualifies.
- (ii) Polychoric qualifies at some `se_scale ≥ 1.0`, with a rate
  roughly flat in `N`.
- (iii) Spearman lies in between and depends on `K`.

**Validation.** Report the selected `se_scale`'s rates on validation
replicates across all cells, including `N = 250` and every `α`.

### 3.3.2 Part B — Structure recovery on ordinal data

**Grid:**

| Factor | Levels |
|---|---|
| Structure | `random_sparse`, `small_world`, `clustered` (from 1.6; truths frozen with 7b) |
| `p` | 10, 20 |
| `N` | 250, 500, 1000 |
| `K` (categories) | 3, 5, 7 |
| skew | symmetric, floor |
| Replicates | Stage 7b timing rule, target 300, floor 150 |

That is 108 cells. If the timing rule gives fewer than 150 replicates,
drop `K = 7` first, then `p = 20` at `N = 250`, in that order. Write
the drop order into the charter before timing.

**Methods** (same draw; `se` from Part A's selection where calibrated):

| Label | Correlation | Estimator |
|---|---|---|
| `gopc_pearson` | Pearson | adjacency engine, current defaults, `se_scale = 1` |
| `gopc_spearman` | Spearman-sine | adjacency engine, current defaults, Part A `se_scale` |
| `gopc_polychoric` | polychoric | adjacency engine, current defaults, Part A `se_scale` |
| `ebic_pearson` | Pearson | `fit_ebicglasso_from_correlation`, `γ = .5` |
| `ebic_polychoric` | polychoric | same; qgraph's usual ordinal practice |
| `pc_polychoric@.01` | polychoric | `pc_stable_skeleton`, Part A `se_scale` |
| `nonreg_bh_polychoric` | polychoric | `fit_nonregularized_ggm_from_correlation`, `q = .05`, Part A `se_scale` |

**Metrics:** as in Stage 7b (structure, weights with refit via the
correlation matrix, strength centrality), plus:

- `polychoric_failures`: the count of fallback pairs
- `repaired`, `max_repair_change`
- `zero_cell_fraction`: the share of empty cells across all pairwise
  tables
- `elapsed_seconds`, including the correlation estimation

For weight refit on ordinal data, fit the constrained GGM on the
**correlation matrix** used. Add `refit_weights_from_correlation(corr,
n, adjacency)` as a thin wrapper around
`gopcnet.metrics.fit._fit_constrained_precision`. Check its signature:
it takes a sample covariance, and a correlation matrix is valid input.

**Gates:**

- **G1:** Part A selection is computed from dev replicates only
  (assertion in the reporting module).
- **G2:** latent truth pairing. The `truth_hash` for `(structure, p,
  replicate)` equals Stage 7b's for the same indices. Use 7b's seed
  derivation for truths, `_STAGE_TAG = 702`, with the truth seed
  independent of `N`, `K` and skew. **Data** seeds use `_STAGE_TAG =
  705`, so the latent data differ from 7b's. That is fine; only the
  truths must match.
- **G3:** on `K = 7` symmetric at `N = 1000`, `gopc_polychoric`'s F1 is
  within `.05` of Stage 7b's archived Gaussian `gopc` F1 for the same
  `(structure, p, N)`. This is a sanity check that fine-grained ordinal
  data behave almost like continuous data. It is distributional, since
  the latent draws differ. If it fails, stop and inspect before
  interpreting anything.

**Questions** (validation replicates; counted within each structure;
`N = 250` included in counts because it is inside the Part A
calibration grid):

- **Q1 — Which correlation input should GOPC use on ordinal data?**
  Per cell, pairwise MCC comparisons among the three GOPC variants,
  with the usual `.01` tolerance and CIs. Predeclared: the **default
  ordinal input** is the calibrated method with the most "best or tied
  best" cells, if it wins in ≥ 60% of cells; otherwise no default, and
  `"auto"` is not implemented.
- **Q2 — Does the niche survive on ordinal data?** Stage 7b's Q2
  criterion with `gopc_<Q1 winner>` vs `ebic_polychoric`. Per
  structure: HOLDS / PARTIAL / FAILS.
- **Q3 — What does ignoring ordinality cost?** `gopc_pearson` vs the Q1
  winner, per `K` and skew. Predeclared expectation: the Pearson
  penalty shrinks as `K` grows and is worst for floor-skewed `K = 3`.
- **Q4 — Practical failure rates.** Polychoric fallbacks, PD repairs
  and zero-cell fractions by `N` and `K`. Descriptive. State plainly if
  polychoric is unreliable at `N = 250` with `K = 7` (sparse tables).
- **Q5 — Comparator context.** `nonreg_bh_polychoric` and
  `pc_polychoric@.01` vs the GOPC winner, reported like Stage 7b's Q3.

**Consequences:**

- A D-entry recording Part A's calibrated `se_scale` values (or "not
  calibrated") and Part B's results.
- If Q1 names a default:
  - set `gopcnet.defaults` `se_scale` values for the calibrated methods
  - implement `correlation="auto"` (all ordinal-like → winner; none →
    Pearson; mixed → `ValueError`)
  - keep `fit_gopc`'s default `correlation="pearson"` unchanged. The
    user opts into `"auto"` explicitly. Changing the default input type
    silently is too surprising for existing users; any later switch
    needs its own D-entry.
- Update `docs/validated_operating_ranges.md`: replace the
  "continuous only" scope statement with the validated ordinal grid
  (`K ∈ {3, 5, 7}`, the two skew patterns, `N ∈ [250, 1000]`, `p ≤ 20`,
  these structures). Keep an explicit statement that binary, nominal,
  mixed and missing data are not validated.
- Add a tutorial section, "Likert data".

### 3.3.3 Implementation

- `src/gopcnet/experiments/stage7e.py` and `stage7e_reporting.py`,
  with the standard conventions.
  - Part A and Part B are separate `--parts` values.
  - The reporting module computes Part A's selection and writes
    `part_a_selection.json`.
  - **Part B's runner reads `part_a_selection.json`.** So Part B runs
    after Part A's aggregation:
    - two sequential workflow dispatches, Part A first; or
    - a local Part A run, since it is cheap (only correlation
      estimation plus one test), followed by a Part B dispatch

    Put the chosen sequence in the charter.
  - Part B's resolved config records the Part A selection file's
    SHA-256.
- Configs:
  - `configs/stage7e_ordinal_partA.yaml`
  - `configs/stage7e_ordinal_partB.yaml`
  - smoke versions of both
- Tests (`tests/unit/test_stage7e.py`):
  - smoke runs of both parts
  - Part B refuses to run without a selection file
  - the selection rule on synthetic rejection-rate data
  - sharded equals unsharded for Part B
  - the `write_report` alias
- Run:
  1. Part A smoke, then Part B smoke (with a smoke selection file,
     clearly marked as smoke)
  2. timing rule
  3. freeze
  4. Part A full run
  5. **⛔ ASK** to dispatch Part B
  6. archive under `evidence/stage7_ordinal/stage7e/`, with `part_a/`
     and `part_b/` subdirectories
  7. D-entry

---

## 3.4 Phase wrap-up

1. Run the full test suite.
2. Update the README: data-type support statement and a quick example
   with `correlation="auto"` if it was authorized.
3. CHANGELOG entries.
4. Handoff note.
5. **⛔ ASK** before committing and before manuscript edits. For the
   manuscript:
   - Section 6.4 loses the "Gaussian only" limitation, restated with
     the validated ordinal scope
   - a new Results subsection
   - Section 3 (Method) gains a paragraph on the correlation input and
     `se_scale`
