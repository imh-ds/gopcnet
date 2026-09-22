# Phase 2 — Lowering the practical sample-size requirement

Read `README.md` in this folder first. Its global rules apply here.

**Prerequisites:**

- Phase 1 is complete and Stage 7b's D-entry is written.
- The user has confirmed the direction after Stage 7b's routing
  (Phase 1, step 1.9).
- If Stage 7b's outcome was B, C or D, re-read this document with the
  user before starting. The routing may narrow or cancel parts of it.

**Goal.** Make GOPC usable, and honest about uncertainty, at the sample
sizes psychologists actually have (`N ≈ 150–500`), without inventing a
new estimator. Three deliverables:

1. **Stage 7c — principled default rules.** Screening and pruning rules
   that are defined at any `N` and `p`, selected on some structure
   families and validated on held-out families. This replaces
   `alpha(N)`, which is fit on six points from one motif family and
   validated only for `N ∈ [700, 3000]`.
2. **Stage 7d — small-N edge-evidence tiers.** A reporting layer that
   sorts every pair into calibrated tiers (strong, moderate, uncertain,
   absent) using per-edge test evidence and bootstrap inclusion,
   instead of a single yes/no graph that is unreliable at small `N`.
3. **Sample-size planner.** Given the expected network and the targets,
   what `N` does a study need? This is engineering plus one decision-log
   entry, not a charter.

**Why this is the main lever for small samples.** At small `N` no
estimator can recover a network reliably. What a method can do is:

- (a) spend its error budget sensibly: specificity first, which is
  EBICglasso's documented weakness
- (b) tell the user which edges are trustworthy
- (c) let the user plan `N` before collecting data

Tuning the fitted `alpha(N)` curve further would not address any of
these.

**Estimated effort.**

- Engineering: 3–4 sessions.
- Stage 7c: one sharded CI run.
- Stage 7d: one sharded CI run.
- Planner: 1 session.

---

## 2.1 Stage 7c — Principled default rules

### 2.1.1 Candidate rules (fix these in the charter before any run)

**Screening rules** (applied to marginal Fisher-z p-values):

| ID | Rule | Rationale |
|---|---|---|
| S0 | `default_screening_alpha(p)` (Phase 0: `.001` for `p ≤ 15`, D-049 interpolation above) | Status quo |
| S1 | Benjamini–Hochberg at `q = .01` (`gopcnet.screening.benjamini_hochberg_threshold`, already implemented and tested) | Adapts to `p` and to how many signals exist automatically. No `p` calibration needed. |
| S2 | Benjamini–Hochberg at `q = .05` | Less conservative variant |

**Pruning rules.** Each gives the alpha for every conditional test:

| ID | Rule |
|---|---|
| P0 | `default_dpi_alpha(N)` (D-012), extrapolated outside `[700, 3000]` and clipped to `[1e-4, .25]` |
| P1 | Power target: `ρ_min = .10`, power `.80` |
| P2 | Power target: `ρ_min = .05`, power `.80` |

**Power-target rule, exact definition.** It picks the **strictest**
alpha at which a true partial correlation of the smallest effect size
of interest (`ρ_min`) is still detected with the target power by one
test at the largest conditioning size `k`:

```
c(N)   = arctanh(ρ_min) · sqrt(N − k − 3) − Φ⁻¹(power)
α(N)   = 2 · (1 − Φ(c(N)))
α_used = clip(α(N), α_lo = .001, α_hi = .20)
```

Here `k = max_conditioning_size` (the rule's own `k`, see C below).

Worked values for `ρ_min = .10`, power `.80`, `k = 4`:

| `N` | Approximate `α(N)` |
|---|---|
| 250 | .47 (clipped to .20) |
| 500 | .17 |
| 1000 | .020 |
| 2000 | .0003 (clipped to .001) |

Put this table in the charter as a sanity check, and recompute it in a
unit test.

This is the "smallest effect size of interest" framing that
psychology reviewers already know. The rule gets stricter as `N`
grows, which is BIC-like and consistent. At small `N` it relaxes to
keep power. The OR-rule across many tests means realized recall will
be below the per-test target. That is why the rule is validated rather
than assumed.

**Conditioning cap:**

| ID | Cap |
|---|---|
| C4 | `max_conditioning_size = 4` (status quo) |
| C2 | `max_conditioning_size = 2` (fewer tests, which may help recall at small `N`) |

**The candidate set** is `{S0, S1, S2} × {P0, P1, P2} × {C2, C4}`: 18
GOPC configurations, all on the adjacency engine from Stage 7a. If
Stage 7a sent 7b to the component engine, **⛔ ASK**: 18
configurations are infeasible there at `p = 30`.

### 2.1.2 API additions (build before chartering; additive only)

In `src/gopcnet/defaults.py`:

```python
def power_target_alpha(n: int, *, rho_min: float, power: float, k: int,
                       alpha_bounds: tuple[float, float] = (0.001, 0.20)) -> float: ...
```

In `fit_gopc`, add `screening_q: float | None = None`. If it is given,
screen with `benjamini_hochberg_threshold(evidence, screening_q)`
instead of `screen_uncorrected`. Passing both `screening_alpha` and
`screening_q` raises `ValueError`. `GOPCResult` records which screen
was used: add a `screening_rule: str | None` field with a default.

**Unit tests:**

1. `power_target_alpha` reproduces the table above to 3 decimals.
2. It is monotone non-increasing in `N`.
3. The clipping works.
4. A BH-screened `fit_gopc` equals a manual BH screen followed by the
   adjacency engine.

### 2.1.3 Design: selection families vs held-out families

This is the key protection against D-065's calibration circularity.
Rules are **selected** on some structure families and **validated** on
others they never saw.

- **Selection families:** `random_sparse` and `small_world`,
  development replicates only.
- **Held-out families:** `random_dense`, `clustered`,
  `random_with_isolates`, plus one **new** family added for this
  charter: `scale_free`.

**`scale_free`** (Barabási–Albert). Add
`barabasi_albert(p, m, rng)` to `gopcnet/generators/psych_networks.py`
as a new function, and register a new structure name. Do not alter the
existing ones (they are frozen with 7b):

- start from a clique on `m + 1` nodes
- attach each new node to `m` distinct existing nodes with probability
  proportional to degree
- use `m = 2`

Hubs are common in symptom networks, and no earlier charter has used
them.

**Grid:**

- `p ∈ {10, 20, 30}`
- `N ∈ {150, 250, 500, 1000, 2000}`
- replicates `R` set by the Stage 7b timing rule, target 500. Split in
  halves: dev and validation.

**Reusing Stage 7b's draws.** Use 7b's `master_seed` and
`_STAGE_TAG = 702` seed derivation, with the `N` index taken from the
tuple `(250, 500, 1000, 2000, 150)`. That keeps 7b's indices for the
shared `N`, and `150` is appended. The data for shared cells then
equals 7b's exactly, thanks to the Cholesky sampler. This is checked by
gate G1.

For shared cells, Stage 7c does **not** refit EBICglasso, PC or the
non-regularized comparators. It pairs with the archived 7b rows by
`(structure, p, N, replicate)`. It **does** fit all comparators for:

- `N = 150`
- the `scale_free` family (new)

**Methods fitted in-run:**

- the 18 GOPC configurations
- `gopc` default (the 7b configuration, for G1)
- comparators only where not archived (see above)

**Metrics:** as in Stage 7b, including MCC and refit-weight metrics.
The GOPC mechanism diagnostics are needed only for the selected rule
and the status quo.

### 2.1.4 Selection procedure (predeclared; applied to development replicates of the selection families only)

1. For each of the 18 configurations, compute mean MCC and mean
   specificity per `(structure, p, N)` cell, then average over cells
   with equal weight per cell.
2. **Feasibility constraint:** in every cell with `N ≥ 250`, mean
   specificity ≥ .95. The error budget goes to specificity first,
   because EBICglasso's weakness is false positives and applied
   researchers interpret edges.
3. Among feasible configurations, choose the one with the highest
   average MCC. **Tie-break:** within `.005` MCC, prefer the simpler
   rule, in this order:
   - screening S0 < S1 < S2
   - pruning P0 < P1 < P2
   - cap C4 < C2

   S0/P0/C4 is the status quo, so a tie keeps the status quo.
4. If no configuration is feasible, relax the constraint to ≥ .93, and
   record that as a predeclared fallback that fired. If still none is
   feasible, **⛔ ASK**.
5. The reporting module asserts that no validation replicate and no
   held-out family entered this computation.

### 2.1.5 Gates and questions

**Gates:**

- **G1:** reproducibility against the 7b archive. The in-run `gopc`
  default reproduces 7b's archived `gopc` rows (`edge_bits` identical)
  in ≥ 99.9% of shared rows. This is the first real test of the
  Cholesky reproducibility fix. If it fails, stop.
- **G2:** the selection assertion in 2.1.4 step 5 passes.

**Questions** (validation replicates only; counted within each
held-out family; cells with `N ≥ 250` counted, `N = 150` reported
separately):

- **Q1 — Does the selected rule generalize?** On held-out families,
  compare the selected rule with the status quo (S0/P0/C4) on MCC:
  - "better": CI entirely above `.01`
  - "comparable": CI lower bound ≥ `−.01`
  - "worse": otherwise

  Predeclared **ADOPT** reading: comparable-or-better in ≥ 90% of
  held-out cells, better in ≥ ⅓ of held-out cells with `N ≤ 500`, and
  median specificity ≥ .95. Otherwise **KEEP STATUS QUO**. If the
  selected rule *is* the status quo, Q1 is moot; report it as such.
- **Q2 — Small-N behavior.** At `N ∈ {150, 250}`, report sensitivity,
  specificity, precision and MCC for the selected rule, the status
  quo, EBICglasso and `nonreg_bh`. Descriptive. State plainly if every
  method's sensitivity is below .5 at `N = 150`; that is the honest
  motivation for Stage 7d.
- **Q3 — Niche check under the new rule.** Stage 7b's Q2 criterion
  (GOPC vs EBICglasso precision and F1) for the selected rule on
  held-out families. Report per family, HOLDS / PARTIAL / FAILS.
- **Q4 — Sensitivity to `ρ_min`.** If a power rule was selected,
  report the P1 vs P2 difference on held-out families. This tells users
  what the `ρ_min` choice costs.

**Consequences:**

- **ADOPT:** a D-entry "Defaults v2". Implement it as follows:
  - `gopcnet.defaults` gets `DEFAULTS_VERSION = "v2"`.
  - `resolve_alphas(..., version="v2")` returns the selected rule's
    settings, including `screening_q` if BH was chosen.
  - `version="v1"` remains available and reproduces Phase 0 exactly.
  - `fit_gopc(..., defaults: Literal["v1", "v2"] = "v2")`.
  - Update the validated-range warnings to the Stage 7c grid (`N ∈
    [150, 2000]`, `p ∈ [10, 30]`, the five structure families). Warn
    below `N = 250` that behavior there was only characterized.
  - CHANGELOG: **breaking behavior change**, with instructions for
    reproducing old results using `defaults="v1"`.
  - Update `docs/validated_operating_ranges.md`, replacing the D-011
    floor language for the default path. D-011 stays true for v1.
- **KEEP STATUS QUO:** a D-entry recording the non-adoption, with the
  numbers. No code change beyond the additive API from 2.1.2.

### 2.1.6 Implementation

- `src/gopcnet/experiments/stage7c.py` and `stage7c_reporting.py`,
  following the conventions in `README.md`, with `_STAGE_TAG` for
  seeding **equal to 702** (deliberately 7b's, for pairing). Put a
  prominent comment on this: it breaks the usual unique-tag rule on
  purpose, and the charter must say so.
- Config: `configs/stage7c_default_rules.yaml` plus a smoke config.
  Fields:
  - `structures_selection`, `structures_heldout`
  - `ps`, `sample_sizes`, `sample_size_seed_order: [250, 500, 1000,
    2000, 150]`
  - `replicates`, split ranges
  - `candidates` (the 18, spelled out explicitly, not generated)
  - `stage7b_archive_path`
- The runner loads the 7b archive only in the reporting step, to pair
  comparator rows. The fitting step never reads it.
- Tests:
  - smoke run
  - sharded equals unsharded
  - the seed-order mapping reproduces 7b's seeds for shared `N` (call
    7b's seed function directly and compare)
  - the selection procedure on a synthetic frame with a known winner
    and a known infeasible configuration
  - the `write_report` alias
- Run: smoke → timing rule → freeze → **⛔ ASK** to dispatch → archive
  under `evidence/stage7_default_rules/stage7c/` → D-entry.

---

## 2.2 Stage 7d — Small-N edge-evidence tiers

### 2.2.1 Relationship to Stage 6a / D-066 (must be stated in the charter)

Stage 6a asked whether survival-fraction ranking finds true *bridges*
better than marginal correlation. It did not meet its predeclared bar,
and per its charter `gopcnet.evidence` was not built.

Stage 7d asks a different, narrower question: are **tiers** built from
bootstrap inclusion and per-edge test evidence **calibrated** against
ground truth at small `N`? It inherits nothing from Stage 6a's result.
It uses a different module name (`gopcnet.edge_evidence`) so nobody
mistakes it for the unbuilt Stage 6a feature. Unmeasured confounding
(D-066) remains a permanent limitation, and the tier documentation
must say so.

### 2.2.2 Build `src/gopcnet/edge_evidence.py` (additive; not re-exported at top level until the D-entry)

```python
@dataclass(frozen=True)
class EdgeEvidenceResult:
    selected: np.ndarray                 # bool (p, p): the point-estimate adjacency
    weights: np.ndarray                  # point-estimate weights
    max_p_value: np.ndarray              # from GOPCResult.diagnostics (adjacency engine)
    inclusion_probability: np.ndarray    # bootstrap, alphas held fixed
    sign_consistency: np.ndarray         # share of bootstrap fits where the edge is present
                                         # with the point estimate's sign (NaN if not selected)
    tier: np.ndarray                     # object/str array (p, p): "strong", "moderate", "uncertain", "absent"
    tier_rule: str                       # version tag, e.g. "tiers-v1"
    bootstraps: int
    screening_alpha: float | None
    dpi_alpha: float
    screening_q: float | None


def edge_evidence(
    data: np.ndarray,
    *,
    bootstraps: int = 200,
    rng: np.random.Generator,
    defaults: str = "v2",   # or whatever fit_gopc's current default is
    **fit_kwargs,
) -> EdgeEvidenceResult:
```

**Procedure:**

1. `point = fit_gopc(data, engine="adjacency", defaults=defaults,
   **fit_kwargs)`. Read the resolved alphas (or `q`) from `point`.
2. Build `fixed = partial(fit_gopc, engine="adjacency", <resolved
   alphas or q>, max_conditioning_size=...)` so that every bootstrap
   refit uses **the same** thresholds. Otherwise `N`-dependent defaults
   would not drift (a bootstrap has the same `N`), but BH-based
   screening thresholds would. Holding the rule fixed is correct for
   BH, since BH is the rule; holding alpha fixed is correct for alpha
   rules. Document which one applies.
3. Make **one** bootstrap pass with the existing
   `gopcnet.stability.bootstrap_replicates(data, fixed, statistic,
   bootstraps=bootstraps, rng=rng)`, where
   `statistic = lambda r: r.weights[np.triu_indices(p, 1)]`. From its
   `replicate_statistics` array (successful × pairs):
   - inclusion = `mean(stats != 0, axis=0)`
   - sign consistency = `mean(sign(stats) == sign(point_weight),
     axis=0)` over all successful replicates, for selected pairs only
   - mirror both to `(p, p)`

   Use the same `ValueError`-exclusion convention the stability tools
   use. Do not also call `bootstrap_edge_stability`; that would double
   the cost.
4. **Tier rule "tiers-v1".** Predeclared, fixed in the charter before
   any run, and **not tuned afterwards**:
   - **strong:** selected, inclusion ≥ .90, and sign consistency ≥ .95
   - **moderate:** selected, inclusion ≥ .60, not strong
   - **uncertain:** (selected and inclusion < .60) or (not selected
     and inclusion ≥ .30). This last group is the "near-miss" set.
   - **absent:** not selected and inclusion < .30

   The thresholds follow common bootnet reporting habits (.5 inclusion
   is bootnet's `bootInclude` default). They are chosen to be simple,
   not optimized. `max_p_value` is recorded for users but is **not**
   part of tiers-v1, which keeps the rule to two inputs. If the charter
   wants to test a `max_p_value`-based variant, it must be a separately
   named rule ("tiers-v1p") evaluated side by side, not a replacement
   chosen after seeing results.

**Unit tests:**

1. Tier assignment on hand-built arrays covering every branch and
   every boundary value.
2. Bootstrap refits use the fixed alphas (monkeypatch `fit_gopc` to
   record its arguments).
3. Reproducibility with a seeded `rng`.
4. Shapes and symmetry.

### 2.2.3 Stage 7d charter (`docs/stage7d_charter.md`)

- **Question:** at `N ∈ {150, 250, 500}`, are tiers-v1 calibrated? Do
  tiers order true-edge rates correctly, and does "strong" mean mostly
  real?
- **Grid:**
  - families: `random_sparse`, `clustered`, `scale_free`
  - `p ∈ {10, 20}` (`p = 30` only if the timing rule allows)
  - `N ∈ {150, 250, 500}`
  - `B = 100` bootstraps (fixed; state that 100 is a compute
    compromise and that `edge_evidence`'s default is 200)
  - replicates `R` by the timing rule, target 300, floor 150
  - fresh `_STAGE_TAG = 704`
- **Truth per pair:** a true edge means `P_ij ≠ 0`.
- **Metrics per cell:**
  - for each tier: the true-edge rate (the share of pairs in that tier
    that are true edges)
  - the share of all true edges landing in each tier
  - the share of **weak** true edges (`|P| < .2`) landing in
    "uncertain" rather than "absent"
  - baselines, computed from the same data:
    - (i) point-estimate-only reporting, i.e. selected vs not
    - (ii) `threshold_by_inclusion_probability(inclusion, .5)`
- **Questions** (validation replicates; counted per family):
  - **Q1 — ordering:** the true-edge rate is strictly decreasing
    across strong > moderate > uncertain > absent (tiers with fewer
    than 20 pairs in a cell are skipped for that cell). Predeclared
    CONFIRMS if ≥ 90% of cells are ordered.
  - **Q2 — strong-tier reliability:** true-edge rate in "strong" ≥ .90
    in ≥ 80% of cells.
  - **Q3 — absent-tier reliability:** the true-negative rate in
    "absent" is ≥ .95 in ≥ 80% of cells.
  - **Q4 — what the extra tiers add:** compared with point-estimate
    reporting, the share of true edges surfaced as strong, moderate or
    uncertain, and the false-edge share in strong plus moderate.
    Descriptive.
  - **Q5 — near-miss value:** the share of weak true edges that the
    point estimate misses but that land in "uncertain". Descriptive.
    This is the practical payoff at small `N`.
- **Consequences:**
  - If Q1–Q3 all confirm: export `edge_evidence` and
    `EdgeEvidenceResult` at the top level; add a tutorial section
    ("reporting a network at small N"); document tiers-v1 in
    `docs/validated_operating_ranges.md` with its validated grid.
  - If any of Q1–Q3 fails: **do not export**. The D-entry records a
    non-confirmation, and **⛔ ASK** whether to redesign the tier rule
    under a new charter.
- **Non-goals:** bridge inference (Stage 6a's topic), unmeasured
  confounding, community detection, `N > 500`.

### 2.2.4 Implementation

- `src/gopcnet/experiments/stage7d.py` and `stage7d_reporting.py`, with
  the standard conventions.
- Raw rows are one row **per replicate** (not per pair) with
  aggregated counts: a tier × truth contingency table (4 × 2 counts)
  flattened into columns, plus weak-edge counts per tier and the two
  baselines' confusion counts. Per-pair rows would be too large
  (`p = 20`: 190 pairs × R × cells).
- Run: smoke → timing rule → freeze → **⛔ ASK** to dispatch → archive
  under `evidence/stage7_edge_evidence/stage7d/` → D-entry.

---

## 2.3 Sample-size planner (engineering + D-entry, no charter)

**Why.** "How many participants do I need?" is the practical question
that decides whether a psychology study can use any network method.
Prior art exists: the `powerly` R package / Constantin et al.'s Monte
Carlo sample-size method for network models (verify the citation).
The contribution here is convenience inside `gopcnet`, not novelty.
Scope the documentation accordingly.

### 2.3.1 Build `src/gopcnet/planning.py` (shipped)

```python
@dataclass(frozen=True)
class PlanTargets:
    sensitivity: float = 0.60
    specificity: float = 0.95
    precision: float | None = None


@dataclass(frozen=True)
class SampleSizePlan:
    table: "pandas.DataFrame"        # one row per N: mean and MC standard error of sensitivity,
                                     # specificity, precision, MCC, strength-centrality rho
    recommended_n: int | None        # smallest N in the grid whose MEAN meets every target
    recommended_n_conservative: int | None  # smallest N whose mean minus 1.96*MC-SE meets every target
    targets: PlanTargets
    assumptions: dict                # structure, p, density, weight mixture, method, alphas, replicates, seed


def plan_sample_size(
    p: int,
    *,
    structure: str = "random_sparse",   # any registered gopcnet.generators.psych_networks structure
    targets: PlanTargets = PlanTargets(),
    n_grid: tuple[int, ...] = (150, 250, 350, 500, 750, 1000, 1500, 2000, 3000),
    replicates: int = 100,
    rng: np.random.Generator,
    fit: Callable[[np.ndarray], GOPCResult] | None = None,   # default: fit_gopc with current defaults
    progress: Callable[[int, int], None] | None = None,
) -> SampleSizePlan:


def edge_detection_power(rho: float, n: int, *, alpha: float, k: int = 0) -> float:
    """Closed-form single-test Fisher-z power, Phi(z - c) + Phi(-z - c) with
    z = arctanh(rho) * sqrt(n - k - 3), c = z_{1 - alpha/2}. This is the formula
    D-065 confirmed against simulation to within .007; it describes ONE test, and
    is an upper bound on GOPC's per-edge recall (the OR-rule over many
    conditioning sets can only lower it)."""
```

**Procedure:**

1. For each replicate, draw one truth with `make_truth(structure, p,
   rng_truth)`.
2. For each `N` in the grid, draw data and fit. Pair truths across `N`,
   as in 7b, so the curve across `N` is smooth.
3. Score each fit with the same metric helpers Stage 7b uses. Move
   those into a shipped location, e.g. `gopcnet/metrics/recovery.py`,
   as new functions. Stage 7b's runner keeps its own imports, which are
   frozen.
4. Build the table, then find `recommended_n` and
   `recommended_n_conservative`. If no `N` meets the targets, return
   `None` and include a message suggesting larger `N` or weaker
   targets.
5. Record every assumption in `assumptions`. The docstring must say:
   "The plan is exactly as good as its assumed network. Run it under
   two or three plausible structures and densities and report the
   range, not one number."

**Tests:**

1. Determinism with a seeded `rng`.
2. On a trivially easy setting (`p = 5`, strong edges only; add a test
   helper structure if needed), `recommended_n` is the smallest grid
   value.
3. `edge_detection_power(rho, n, alpha=a, k=1)` equals
   `3 * stage5i_reporting.predicted_weak_edge_recall(rho, n, a) - 2` on
   a few inputs. That function computes the triangle recall
   `(2 + power)/3` with one conditioning variable, `sqrt(n - 1 - 3)`.
4. With `replicates=10` and a coarse grid, the whole call finishes in
   under 60 s at `p = 10` (mark slow if needed).
5. **Integration check:** for one configuration, `recommended_n`'s
   mean sensitivity reproduces within 2 MC-SE on a fresh seed.

**Docs:**

- A tutorial section, "Planning a study", after the fitting section.
- A README bullet.
- CHANGELOG "Added".
- A D-entry (engineering convention) covering:
  - the targets' defaults, and why specificity is .95
  - the conservative variant
  - the prior-art statement
  - the fact that the planner inherits the validated range of whatever
    `fit` it uses

---

## 2.4 Phase wrap-up

1. Run the full test suite.
2. Update `docs/validated_operating_ranges.md` with:
   - a "Defaults v2" section, or the recorded non-adoption
   - an "Edge-evidence tiers" section, only if confirmed
   - a "Planning" note
3. Update the README quick-start if the defaults or tiers changed.
4. Write a handoff note in `docs/handoff/`.
5. **⛔ ASK** before committing and before any manuscript edit. For
   the manuscript: a new Results subsection for Stage 7c/7d, and
   Section 6.1 ("Practical guidance") rewritten around defaults v2,
   tiers, and planning.
