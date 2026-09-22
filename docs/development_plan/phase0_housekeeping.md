# Phase 0 — Housekeeping and a real default

Read `README.md` in this folder first. Its global rules apply here.

**Goal.** Close every loose end from the D-065/Stage 6a arc, and make
the "one fixed default" that D-065 argues for something a user can
actually call. No simulation charter is needed in this phase. Each
step is engineering, archiving, or a decision-log entry.

**Estimated effort.** 1–2 working sessions.

**Done when:**

- D-066 is written.
- Stage 6a evidence is archived.
- `fit_gopc(data)` runs with no alpha arguments, resolves documented
  defaults, and warns outside the validated range.
- A Cholesky sampler exists and is tested.
- The tutorial and README use the defaults.
- The full test suite passes.
- A short handoff note is written.

---

## Step 0.1 — Verify the state the handoff describes

The handoff says the D-065 addendum to
`docs/validated_operating_ranges.md` was "drafted but NOT committed".
Commit `652b6d4` ("add D-065 addendum to validated operating ranges")
suggests it has since been committed.

1. Run `git status` and `git log --oneline -5`.
2. Run
   `git show --stat 652b6d4 -- docs/validated_operating_ranges.md`.
3. Search `docs/validated_operating_ranges.md` for "D-065" and confirm
   the addendum is present. It should contain the recall-gap
   correction, the precision finding, and the `overlap` sampler caveat.
4. Record the result in your session notes. If it is committed, drop
   this item from the TODO list. If it is not, **⛔ ASK** the user
   before committing.

`manuscript/` is gitignored on purpose. Never add it.

## Step 0.2 — Archive the Stage 6a evidence

The full Stage 6a run exists only as a GitHub Actions artifact, and
artifacts expire. The most recent successful `Sharded benchmark
(generic)` run at the time of writing was **35703700288**
(2026-09-22, 2h58m). Confirm it is the Stage 6a run before using it.

1. Identify the run:

   ```bash
   gh run view 35703700288 --json displayTitle,createdAt,conclusion,jobs
   ```

   Check that the jobs' shard names or inputs reference
   `gopcnet.experiments.stage6a`. If they don't, run
   `gh run list --workflow sharded_benchmark.yml --limit 10` and find
   the right one. If it's still ambiguous, **⛔ ASK**.
2. **⛔ ASK before downloading.** Downloading counts as an action
   needing explicit permission. Tell the user the run ID, the artifact
   names (`gh run view <id> --json artifacts` or
   `gh api repos/imh-ds/gopcnet/actions/runs/<id>/artifacts`), and
   their sizes. The user may already have a local copy. The handoff
   says it was "downloaded", so ask for its path first.
3. With permission, download into the scratchpad, not the repository:

   ```bash
   gh run download <id> -D <scratchpad>/stage6a_artifacts
   ```

4. Find the aggregated artifact: the one containing `raw_metrics.csv`,
   `report.json`, `stage6a_report.md`, and figures. If only shard
   artifacts exist, or the aggregate step failed as in Stage 5i,
   re-aggregate locally:

   ```bash
   python scripts/aggregate_shards.py --module gopcnet.experiments.stage6a --config configs/stage6a_<full>.yaml --shards-dir <scratchpad>/stage6a_artifacts --output <scratchpad>/stage6a_aggregated
   ```

   `--shards-dir` must hold one subdirectory per shard, each with its
   own `raw_metrics.csv`. Use `ls configs/stage6a_*` to find the
   non-smoke config. The aggregator verifies row count and full
   coverage. If either check fails, stop and **⛔ ASK**.
5. Create `evidence/stage6_evidence_tiers/stage6a_bridge_validation/`.
   That is the path the Stage 6a charter's "Required evidence" section
   specifies. Copy in:
   - `raw_metrics.csv`, gzipped to `raw_metrics.csv.gz` with
     `gzip -9 -k` if over 50 MB
   - `report.json`, `resolved_config.yaml`, `metadata.json`,
     `stage6a_report.md`
   - all figures
   - `shard_metadata.json` if the aggregator produced one
6. Verify integrity:
   - `metadata.json`'s `charter_sha256` must equal
     `sha256sum docs/stage6a_charter.md`. If it doesn't, the charter
     was edited after the run. Record that as a disclosed discrepancy
     in D-066; do not "fix" either file.
   - The row count must equal `stage6a.expected_row_count(config)`.
7. Create `evidence/stage6_evidence_tiers/README.md` mirroring
   `evidence/stage5_benchmarks/README.md`: a one-paragraph purpose
   statement, then a table (Directory | Decision | Source) with one row
   linking the Actions run and noting any local re-aggregation.

## Step 0.3 — Write D-066 (Stage 6a result)

The handoff frames this as an open judgment call. It is less open than
it looks: `docs/stage6a_charter.md`'s own "Consequences" section
already predeclares the outcome:

> "If Q1 does not replicate at the predeclared threshold, the feature
> is not built as proposed, and the scratch finding is recorded in the
> decision log as a non-replicated preliminary result, not silently
> dropped."

Follow the charter.

1. Read `stage6a_report.md` and `report.json` in full. Extract:
   - **G1:** the survival-fraction vs `pMax` top-1 agreement rate on
     `confound_trap_observed`, per cell. Pass requires ≥ .95 at every
     cell. If G1 failed, D-066 is about that failure, and Q1–Q5 are
     reported as uninterpretable per the charter.
   - **Q1:** the fraction of `(rho_bridge, rho_confound, N)` cells where
     the survival-fraction top-1 rate exceeds the marginal-correlation
     top-1 rate by ≥ .20. The predeclared bar is ≥ 80% of cells.
   - **Q2–Q5:** read off as the charter specifies, including Q3's
     predeclared ratios: ≥ 3× shrinkage from `N = 500` to `N = 3000` for
     `confound_trap_observed`, and < 1.5× for `confound_trap_latent`.
   - Any disaggregated view (per bridge strength or confound strength)
     that the report or the handoff's conversation relied on.
2. Write the entry with the README template:
   - **Title:** state the result plainly, e.g. "Stage 6a: survival-
     fraction bridge ranking does not meet its predeclared Q1 bar;
     per-cell pattern consistent with mechanism (exploratory);
     unmeasured-confound false-bridge rate flat in N, as predicted".
     Adjust to the actual numbers.
   - **Status:** "Descriptive, one hard gate (G1): <PASSED/FAILED>".
   - **Q1:** the literal predeclared result first, then the
     disaggregated pattern in a clearly labeled paragraph beginning
     "**Post-hoc, not predeclared:**". Explain the ceiling effect at
     strong bridges as a candidate explanation, not an established
     one.
   - **Q3:** report the observed-vs-latent false-confirmation curves.
     This is the charter's central exhibit, and the unmeasured-confound
     limitation must be stated as permanent.
   - **Decision:** "Per the charter's own Consequences section, the
     `gopcnet.evidence` module is **not built as proposed**." Add: "The
     per-edge statistics it would have exposed (maximum p-value across
     tested conditioning sets, survival fraction, separating set) are
     reconsidered under a new, separately chartered question (Stage 7d:
     small-sample edge-evidence tiers), which asks a different question
     (calibration of evidence tiers against ground truth) and does not
     inherit Stage 6a's result."
   - **Consequences:**
     - Add the unmeasured-confounding limitation to
       `docs/validated_operating_ranges.md` as a standing caveat
       (edit in Step 0.3.4).
     - Nothing in the package changes.
     - Include the evidence path and charter SHA-256.
3. Add a row for Stage 6a / D-066 to the handoff-style evidence table
   in `docs/validated_operating_ranges.md`'s comparator section, or
   wherever that document lists per-charter results. Keep the existing
   format.
4. Add a short "Unmeasured confounding (Stage 6a, D-066)" paragraph to
   `docs/validated_operating_ranges.md`. It should say:
   - Any conditional-independence method, GOPC included, can keep a
     spurious edge whose association comes from an unobserved common
     cause.
   - Stage 6a measured the false-bridge rate at about 10–12%, flat in
     `N`. Use the report's actual numbers.

**⛔ ASK** the user to review the D-066 draft before anything is
committed. The user flagged this as a judgment call.

## Step 0.4 — Add a reproducible Cholesky sampler

**Why.** D-065 diagnosed that `Generator.multivariate_normal` factors
the covariance by SVD. With a repeated singular value, the rotation
within the degenerate subspace depends on the machine's floating
point, so draws are not bitwise reproducible across machines. Cholesky
factorization is unique for a positive-definite matrix, so draws
become a deterministic function of `(seed, covariance)`, up to
last-bit floating-point differences in `L`, which do not cascade the
way an SVD rotation does.

**Where.** A new **shipped** subpackage, `src/gopcnet/generators/`,
with an `__init__.py` and the module `sampling.py`. It must not go
under `gopcnet/simulation/`: `pyproject.toml` excludes
`gopcnet.simulation*` from the built package, and Phase 2's
sample-size planner (a user-facing tool) needs both the sampler and the
Phase 1 network generators at install time. Do not change the
`pyproject.toml` excludes. `gopcnet.generators` is picked up
automatically by `packages.find`. Add a test to
`tests/unit/test_package_api.py` confirming `gopcnet.generators` is
importable.

**Code:**

```python
"""Reproducible multivariate-normal sampling for new DGPs (D-065 follow-up).

Every DGP added after D-065 must draw through this module, never through
`numpy.random.Generator.multivariate_normal`, whose SVD factorization is not
uniquely determined when the covariance has a repeated singular value (the
cause of Stage 5i's G1/G2 failures on `overlap`). Existing samplers are
frozen and are not migrated.
"""

from __future__ import annotations

import numpy as np


def cholesky_factor(covariance: np.ndarray) -> np.ndarray:
    """Lower-triangular L with L @ L.T == covariance. Raises ValueError if the
    matrix is not symmetric positive definite."""
    cov = np.asarray(covariance, dtype=float)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError("covariance must be a square matrix")
    if not np.allclose(cov, cov.T, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    try:
        return np.linalg.cholesky(cov)
    except np.linalg.LinAlgError as exc:
        raise ValueError("covariance must be positive definite") from exc


def sample_gaussian(covariance: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Draw n rows from N(0, covariance) as standard_normal((n, p)) @ L.T."""
    if n < 1:
        raise ValueError("n must be positive")
    factor = cholesky_factor(covariance)
    return rng.standard_normal((n, factor.shape[0])) @ factor.T


def covariance_from_precision(precision: np.ndarray) -> np.ndarray:
    """Invert a precision matrix and symmetrize away round-off."""
    covariance = np.linalg.inv(np.asarray(precision, dtype=float))
    return (covariance + covariance.T) / 2.0
```

**Tests** (`tests/unit/test_sampling.py`):

1. `sample_gaussian(cov, n, default_rng(0))` returns the same array
   twice.
2. Covariance recovery: at `n = 200_000` with `p = 5` and a random PD
   covariance, `np.cov(x, rowvar=False)` is within `0.02` elementwise.
3. **A covariance with a repeated eigenvalue** (e.g. the `overlap`
   precision's inverse from `simulation/motifs.py`) samples without
   error and reproducibly. This is the D-065 case.
4. A non-PD matrix raises `ValueError`, and so does an asymmetric one.

**Decision log.** A short "Engineering convention" entry: "New DGPs
sample via Cholesky (`gopcnet.generators.sampling`); existing samplers
frozen; motivation D-065." It can be combined with Step 0.5's entry if
both land together.

## Step 0.5 — Ship the default: `fit_gopc(data)` with resolved alphas

**Why.** D-065 reframes GOPC's contribution as "one fixed default is
robust across regimes". Today `fit_gopc` has **no defaults**: both
alphas are required keyword arguments. `alpha(N)` lives only in
`gopcnet.experiments.stage1j_fit`, which is excluded from the package,
and the tutorial calls `fit_gopc(data, screening_alpha=0.05,
dpi_alpha=0.05)`, which is not the validated setting. The paper's
central claim is not something a user can currently call.

**This is not a mechanism change.** Explicit-alpha calls must stay
bit-identical. Only the behavior when the arguments are omitted is new.

### 0.5.1 The default rules (exact current evidence, nothing new)

- **Pruning:** `dpi_alpha(N) = a + b * ln(N)`, the `linear_log_n` form
  selected in D-012. Do not retype the rounded constants
  (`0.5222`, `-0.0566`). Compute the exact parameters once:

  ```python
  from gopcnet.experiments.stage1j_fit import fit_candidate_forms, select_form
  form = select_form(fit_candidate_forms())
  print(form.name, repr(form.parameters))
  ```

  Paste the full-precision `repr` values into the new module as
  constants, with a comment citing D-012 and this derivation. A unit
  test (run from the checkout, where `experiments` is importable)
  asserts the constants equal `form.parameters` to `1e-15`.
- **Validated range for pruning:** `N ∈ [700, 3000]` (D-012), with a
  recommended floor of `N ≥ 750` (D-011).
- **Screening:** the D-049 log-linear interpolation between
  `(p = 15, α = .001)` and `(p = 30, α = .0001)`, copied exactly from
  `gopcnet.experiments.stage5c._screening_alpha_for_p`, **with one
  guard.** For `p ≤ 15`, return `.001` (the value D-047 used at both
  `p = 3` and `p = 15`). The raw interpolation *increases* below
  `p = 15`: it gives about `.21` at `p = 3`, which was never validated.
  Clamping to `.001` reproduces every archived `p ≤ 15` configuration.
- **Validated range for screening:** `p ∈ [3, 27]`. Stage 5c tested the
  interpolation up to `p = 27`, and `p = 30` is an anchor from Stage 2.
  Treat `p > 30` as extrapolation.

### 0.5.2 New public module `src/gopcnet/defaults.py`

```python
"""Default significance levels for fit_gopc (see docs/decision_log.md,
the defaults-API entry, and D-011/D-012/D-049 for the evidence behind each).
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

# Exact linear_log_n parameters from gopcnet.experiments.stage1j_fit (D-012).
_DPI_A = ...  # paste full-precision repr
_DPI_B = ...

_SCREEN_P_LOW, _SCREEN_ALPHA_LOW = 15.0, 0.001    # D-049 anchors (Stage 2)
_SCREEN_P_HIGH, _SCREEN_ALPHA_HIGH = 30.0, 0.0001

DPI_VALIDATED_N = (700, 3000)      # D-012
DPI_RECOMMENDED_MIN_N = 750        # D-011
SCREEN_VALIDATED_P = (3, 27)       # D-047 (p=3, 15), D-049 (up to 27)


class OutsideValidatedRangeWarning(UserWarning):
    """Emitted when a default is used outside the range it was validated on."""


def default_dpi_alpha(n: int) -> float: ...
def default_screening_alpha(p: int) -> float: ...


@dataclass(frozen=True)
class ResolvedAlphas:
    screening_alpha: float
    dpi_alpha: float
    screening_source: str   # "user" | "default"
    dpi_source: str         # "user" | "default"
    warnings: tuple[str, ...]


def resolve_alphas(n: int, p: int, screening_alpha: float | None, dpi_alpha: float | None) -> ResolvedAlphas: ...
```

Behavior, specified exactly:

- `default_dpi_alpha(n)`:
  - Raise `ValueError` if `n < 4`.
  - Compute `a + b * ln(n)`.
  - If the result is ≤ 0 (which happens at `N ≳ 10,000`), clip to
    `1e-4` and warn.
  - If `n` is outside `[700, 3000]`, emit
    `OutsideValidatedRangeWarning`. The message must name the range and
    say the value is extrapolated.
  - If `700 ≤ n < 750`, emit the same warning class with the D-011
    thin-margin wording.
  - Never raise for small `n`. Users need *something*; the warning
    carries the caveat.
- `default_screening_alpha(p)`:
  - Raise `ValueError` if `p < 2`.
  - Return `.001` for `p ≤ 15`, else the interpolation.
  - Warn if `p > 30`.
- `resolve_alphas(...)`:
  - Fill each `None` from the matching default.
  - Validate user-supplied values with `0 < α < 1`.
  - Warn if `screening_alpha > dpi_alpha`. The design assumes the
    screen is the stricter test. Don't raise; the Stage 5i matched-alpha
    configurations set them equal.
  - Return the `ResolvedAlphas` record.

### 0.5.3 Change `fit_gopc` and `fit_gopc_fixed_order`

In `src/gopcnet/pipeline/gopc.py`:

1. Change the signatures to

   ```python
   def fit_gopc(
       data,
       *,
       screening_alpha: float | None = None,
       dpi_alpha: float | None = None,
       max_conditioning_size: int = 4,
   ) -> GOPCResult:
   ```

   Do the same for `fit_gopc_fixed_order`, without
   `max_conditioning_size`.
2. At the top of each function:

   ```python
   n, p = np.asarray(data).shape
   alphas = resolve_alphas(n, p, screening_alpha, dpi_alpha)
   ```

   Then use `alphas.screening_alpha` and `alphas.dpi_alpha` exactly
   where the old arguments were used.
3. Extend `GOPCResult` **backward-compatibly**. Add trailing fields
   with defaults so positional construction elsewhere keeps working:

   ```python
   screening_alpha: float | None = None
   dpi_alpha: float | None = None
   ```

   Populate them. This lets users report the settings they actually
   used, which matters for reproducible psychology papers.
4. Update both docstrings:
   - The parameters section now describes the defaults and cites the
     decision-log entries.
   - Add a "Defaults and validated range" paragraph.
   - Change the examples to `fit_gopc(data)`. The doctest data has
     `N = 500`, so the example must show or suppress the warning, e.g.
     wrap it in `warnings.catch_warnings()` in the doctest, or use
     `# doctest: +SKIP` on the warning line. The existing doctests with
     explicit alphas must still pass unchanged.
5. Export from `src/gopcnet/__init__.py`: `default_dpi_alpha`,
   `default_screening_alpha`, `resolve_alphas`, `ResolvedAlphas`,
   `OutsideValidatedRangeWarning`. Add them to `__all__`. Update
   `tests/unit/test_package_api.py` if it checks `__all__`.
6. `bootstrap_edge_stability`, `case_drop_bootstrap`,
   `network_comparison_test` and similar tools take a `fit` callable.
   With defaults, `fit_gopc` is now a valid `fit` directly, without
   `partial`. Note in each tool's docstring that alphas are **re-resolved
   per resample**: on a case-drop subsample, `N` shrinks, so
   `dpi_alpha` changes. Decide the convention, **⛔ ASK** if unsure, and
   document it. Recommended: document that users who want a fixed alpha
   across resamples should pass it explicitly
   (`partial(fit_gopc, dpi_alpha=resolve_alphas(...).dpi_alpha, ...)`),
   and show that in the tutorial. Case-drop bootstrap (CS-coefficient)
   in particular should hold alphas fixed at the full-sample values so
   stability isn't confounded with alpha drift. Implement this by
   having the tutorial pass fixed alphas. Do not change the stability
   functions.

### 0.5.4 Tests (`tests/unit/test_defaults.py`, plus additions to `test_gopc.py`)

1. The constants equal the D-012 fit (see 0.5.1).
2. `default_dpi_alpha(750)`, `(1000)`, `(1500)`, `(1750)` equal the
   `alpha_by_n` values recorded in
   `evidence/stage5_benchmarks/stage5i_pc_alpha_sweep/resolved_config.yaml`
   (`d012_alpha_by_n`) to `1e-12`. This ties the default to the
   archived evidence.
3. `default_screening_alpha(15) == .001`, `(30) == .0001` (within
   `1e-15` relative), and `(3) == .001` (the clamp).
   `default_screening_alpha(p)` equals `stage5c._screening_alpha_for_p(p)`
   for `p ∈ {15, 20, 24, 27}`.
4. Warnings: `pytest.warns(OutsideValidatedRangeWarning)` for
   `n = 300`, `n = 5000`, `n = 720`, and `p = 40`. No warning for
   `n = 1000, p = 15` (use `warnings.simplefilter("error")`).
5. **Regression:** for three random datasets, `fit_gopc(data,
   screening_alpha=.001, dpi_alpha=.13)` has the same adjacency and
   weights as the pre-change function. Before editing, save the
   pre-change outputs as a small `.npz` fixture in `tests/fixtures/`,
   generated by a script you delete afterward, or compute them inline
   by calling `growing_subset_dpi` directly as `test_gopc.py` already
   does.
6. `fit_gopc(data)` with `N = 1000`, `p = 15` equals `fit_gopc(data,
   screening_alpha=.001, dpi_alpha=default_dpi_alpha(1000))`.
7. `GOPCResult` records the resolved alphas.

### 0.5.5 Decision-log entry: defaults API

"Engineering convention" status. Record:

- the exact formulas and constants
- the `p ≤ 15` clamp, and why
- the validated ranges
- the warning policy
- that explicit-alpha calls are unchanged, so every archived result
  still reproduces
- the resampling convention chosen in 0.5.3 step 6
- that the defaults are the **current best evidence, not a final
  answer**: Stage 7c (Phase 2) is chartered to replace them with rules
  defined at any `N` and validated on held-out structure families

## Step 0.6 — Update the tutorial, README, and CHANGELOG

1. `examples/tutorial.py`: the simulated data has `N = 600`, `p = 8`.
   - Change section 3 to `result = gopcnet.fit_gopc(data)`. Capture and
     print the warning; `N = 600` is below the validated floor. Add a
     markdown cell explaining what the warning means and pointing to
     `docs/validated_operating_ranges.md`'s "Practical translation for
     smaller-N datasets". This is honest and shows users the caveat
     system working.
   - Print `result.screening_alpha` and `result.dpi_alpha`.
   - Replace every `partial(gopcnet.fit_gopc, screening_alpha=0.05,
     dpi_alpha=0.05)` with fixed resolved alphas (see 0.5.3 step 6).
   - Regenerate `tutorial.ipynb` with whatever script or process the
     repository uses. Check `examples/README.md`. D-064 says the `.py`
     file is the source of truth. `tutorial_rendered.html` stays
     untracked.
   - Run the tutorial end to end (`python examples/tutorial.py`) and
     confirm it finishes.
2. `README.md`: the quick-start shows `fit_gopc(data)`, plus a one-line
   description of the defaults and a link to the operating-ranges doc.
3. `CHANGELOG.md` under `[Unreleased]`:
   - "Added: default significance levels (`gopcnet.defaults`)"
   - "Changed: `fit_gopc`/`fit_gopc_fixed_order` alphas are now
     optional"
   - "Added: `GOPCResult.screening_alpha`/`.dpi_alpha`"
4. `src/gopcnet/__init__.py` module docstring: update the examples at
   lines ~16, 36, 61, 126, 154, which use explicit `.01/.05` alphas, to
   the default form where that's natural. Keep one explicit-alpha
   example to show the override.

## Step 0.7 — Wrap up

1. Run `python -m pytest` and make sure everything passes. No doctest
   run is configured in `pyproject.toml` or CI at the time of writing,
   so also run `python -m pytest --doctest-modules src/gopcnet/pipeline/gopc.py src/gopcnet/defaults.py`
   to check the examples you changed.
2. Write `docs/handoff/<date>_phase0_complete.md`. That folder is
   gitignored, so it stays local. List what was done, the D-numbers
   assigned, and anything deferred.
3. **⛔ ASK** the user whether to commit. Suggested split:
   - evidence and D-066
   - the sampler
   - the defaults API, docs, and tutorial

   Use the attribution line in the session's system instructions.
