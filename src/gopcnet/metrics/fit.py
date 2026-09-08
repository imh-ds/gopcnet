"""Absolute goodness-of-fit for a fitted network -- distinct from
everything else in `gopcnet.metrics`/`gopcnet.stability`, which all
ask "how reliable is this specific edge/structure," never "does this
structure fit the data well at all."

`fit_gaussian_graphical_model` takes any adjacency matrix (from any of
this package's four fit functions -- not GOPC-specific) plus the data
it was estimated from, and fits the exact maximum-likelihood Gaussian
graphical model constrained to that adjacency's zero pattern: the
precision matrix whose off-diagonal entries are exactly zero at every
non-edge, and which otherwise matches the sample covariance exactly on
the diagonal and at every edge (covariance selection; Speed & Kiiveri,
1986; Whittaker, 1990) -- computed via iterative proportional scaling,
a block-coordinate-descent algorithm closely related to the graphical
lasso's own (Friedman, Hastie, & Tibshirani, 2008) but without an L1
penalty, since the support is already fixed rather than being searched
for.

From that fit, `log_likelihood`, `aic`, `bic`, and `ebic` (Foygel &
Drton, 2010) fall out directly -- a single number a user can report
for whichever method they used, and a common yardstick to compare a
GOPC structure against `fit_ebicglasso`'s or `fit_pc_skeleton`'s on
the same data. See `docs/decision_log.md`'s D-058 for why AIC/BIC and
EBIC count free parameters differently (not an inconsistency -- it's
what each statistic's own literature definition specifies).

`fit_indices` adds the SEM-tradition fit indices (RMSEA, CFI, TLI,
SRMR) on top of the same machinery: it calls `fit_gaussian_graphical_model`
three times -- once for `adjacency` itself, once for the saturated
model (every edge present, the best any structure on this many
variables could possibly fit), and once for the null/independence
model (no edges at all, `fit_gaussian_graphical_model`'s own
empty-graph case) -- and combines their log-likelihoods into a
model chi-square, degrees of freedom, and the four indices. See
`docs/decision_log.md`'s D-059 for the exact formulas and the
conventional cutoffs' own validation status (none, for a sparse
structure-learning method like GOPC or PC -- these cutoffs come from
the SEM literature, not this package's own benchmarks).

`train_test_fit_indices` addresses a specific bias in the two
functions above when they're called the obvious way (fit the
structure on a dataset, then evaluate its own fit against that same
dataset): the structure wasn't fixed in advance, it was *searched for*
on this exact sample by whichever fit function produced it, so part of
how well it then appears to fit is the search finding and exploiting
this sample's own noise, not just recovering genuine population
structure. Splitting the data, fitting the structure on one part and
evaluating `fit_indices` on the other, removes that optimism. See
`docs/decision_log.md`'s D-060.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np
from scipy.stats import chi2 as _chi2_distribution


def _fit_constrained_precision(
    sample_covariance: np.ndarray,
    adjacency: np.ndarray,
    *,
    max_iter: int,
    tol: float,
) -> tuple[np.ndarray, np.ndarray, bool, int]:
    """Iterative proportional scaling: repeatedly regress each variable
    on its graph neighbors only (using the *current* working covariance
    `w` for the neighbors' own cross-terms, not the sample covariance --
    the same block-update `w12 = W11 @ beta` the graphical lasso itself
    uses), until `w` stops changing. Returns the fitted precision
    matrix, the converged working covariance, whether it converged
    within `max_iter`, and how many iterations it took."""
    p = sample_covariance.shape[0]
    w = sample_covariance.copy()
    converged = False
    iterations = 0

    for iteration in range(1, max_iter + 1):
        iterations = iteration
        max_change = 0.0
        for i in range(p):
            others = np.array([k for k in range(p) if k != i])
            neighbor_mask = adjacency[i, others]
            previous_column = w[others, i].copy()

            new_column = np.zeros(len(others))
            if neighbor_mask.any():
                neighbor_idx = others[neighbor_mask]
                w_neighbors = w[np.ix_(neighbor_idx, neighbor_idx)]
                s_neighbors = sample_covariance[neighbor_idx, i]
                try:
                    beta_neighbors = np.linalg.solve(w_neighbors, s_neighbors)
                except np.linalg.LinAlgError as exc:
                    raise ValueError(
                        "singular neighbor covariance submatrix; cannot fit the constrained MLE"
                    ) from exc
                beta_full = np.zeros(len(others))
                beta_full[neighbor_mask] = beta_neighbors
                w_others = w[np.ix_(others, others)]
                new_column = w_others @ beta_full

            w[others, i] = new_column
            w[i, others] = new_column
            if len(others):
                max_change = max(max_change, float(np.max(np.abs(new_column - previous_column))))

        if max_change < tol:
            converged = True
            break

    try:
        precision = np.linalg.inv(w)
    except np.linalg.LinAlgError as exc:
        raise ValueError("fitted covariance is singular; cannot invert to a precision matrix") from exc

    return precision, w, converged, iterations


def _gaussian_log_likelihood(precision: np.ndarray, sample_covariance: np.ndarray, n: int) -> float:
    p = precision.shape[0]
    sign, log_det = np.linalg.slogdet(precision)
    if sign <= 0:
        raise ValueError("fitted precision matrix is not positive definite")
    return 0.5 * n * (log_det - p * np.log(2 * np.pi) - np.trace(sample_covariance @ precision))


@dataclass(frozen=True)
class GGMFitResult:
    """The constrained Gaussian graphical model MLE for one adjacency
    matrix and dataset, plus its goodness-of-fit.

    `precision` is the fitted, exactly-zero-at-non-edges precision
    matrix; `covariance` is its inverse (matches the sample covariance
    exactly on the diagonal and at every edge -- the defining property
    of covariance selection, not an approximation). `n_parameters` is
    `n_variables + n_edges` (the diagonal precision entries plus the
    edges) -- what `aic`/`bic` count as free parameters. `ebic` uses
    `n_edges` alone, per Foygel & Drton's (2010) own derivation; see
    `docs/decision_log.md`'s D-058. `converged`/`n_iterations` report
    whether the fitting algorithm actually converged within `max_iter`
    -- check this before trusting the fit on a large or poorly
    conditioned network.
    """

    precision: np.ndarray
    covariance: np.ndarray
    log_likelihood: float
    n_parameters: int
    n_edges: int
    aic: float
    bic: float
    ebic: float
    ebic_gamma: float
    converged: bool
    n_iterations: int


def fit_gaussian_graphical_model(
    data: np.ndarray,
    adjacency: np.ndarray,
    *,
    ebic_gamma: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> GGMFitResult:
    """Fit the exact MLE Gaussian graphical model constrained to
    `adjacency`'s zero pattern, and report its goodness-of-fit.

    Parameters
    ----------
    data : np.ndarray
        ``(n_samples, n_variables)`` array of continuous, approximately
        Gaussian observations -- the same data `adjacency` was
        estimated from (an adjacency evaluated against a *different*
        dataset than it was fit on is a valid call, e.g. out-of-sample
        fit checking, but that use case is on the caller).
    adjacency : np.ndarray
        ``(n_variables, n_variables)`` boolean, symmetric, zero-diagonal
        adjacency matrix -- from any of this package's four fit
        functions, or your own.
    ebic_gamma : float, default 0.5
        EBIC's own hyperparameter (Foygel & Drton, 2010); `0.5` matches
        `fit_ebicglasso`'s own default (`qgraph`'s package convention).
    max_iter, tol : the fitting algorithm's own convergence controls.

    Returns
    -------
    GGMFitResult

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc, fit_gaussian_graphical_model
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> result = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    >>> fit = fit_gaussian_graphical_model(data, result.adjacency)
    >>> fit.aic, fit.bic, fit.ebic  # doctest: +SKIP
    """
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("data must be a two-dimensional array")
    n, p = values.shape

    adjacency_bool = np.asarray(adjacency, dtype=bool)
    if adjacency_bool.shape != (p, p):
        raise ValueError("adjacency must be a (n_variables, n_variables) matrix matching data's column count")
    if not np.array_equal(adjacency_bool, adjacency_bool.T):
        raise ValueError("adjacency must be symmetric")
    if np.any(np.diag(adjacency_bool)):
        raise ValueError("adjacency must have a False diagonal")
    if n <= p:
        raise ValueError("data must have more rows than columns for the sample covariance to be invertible")
    if not (0.0 < ebic_gamma <= 1.0):
        raise ValueError("ebic_gamma must be in (0, 1]")

    sample_covariance = np.cov(values, rowvar=False, ddof=0)  # MLE covariance (divisor n)

    precision, covariance, converged, iterations = _fit_constrained_precision(
        sample_covariance, adjacency_bool, max_iter=max_iter, tol=tol
    )
    log_likelihood = _gaussian_log_likelihood(precision, sample_covariance, n)

    n_edges = int(np.triu(adjacency_bool, k=1).sum())
    n_parameters = p + n_edges

    aic = -2.0 * log_likelihood + 2.0 * n_parameters
    bic = -2.0 * log_likelihood + n_parameters * np.log(n)
    ebic = -2.0 * log_likelihood + n_edges * np.log(n) + 4.0 * ebic_gamma * n_edges * np.log(p)

    return GGMFitResult(
        precision=precision,
        covariance=covariance,
        log_likelihood=log_likelihood,
        n_parameters=n_parameters,
        n_edges=n_edges,
        aic=aic,
        bic=bic,
        ebic=ebic,
        ebic_gamma=ebic_gamma,
        converged=converged,
        n_iterations=iterations,
    )


def _correlation_matrix(covariance: np.ndarray) -> np.ndarray:
    scale = np.sqrt(np.diag(covariance))
    return covariance / np.outer(scale, scale)


@dataclass(frozen=True)
class FitIndicesResult:
    """SEM-tradition fit indices for one adjacency matrix and dataset,
    built from three `fit_gaussian_graphical_model` calls (`target`,
    `saturated` -- every edge present, `null` -- no edges at all).

    `chi_square`/`df`/`p_value` are the model chi-square test against
    the saturated model (`p_value` is the probability of a chi-square
    this large under the null hypothesis that `adjacency` is the true
    structure -- a *small* `p_value` is evidence *against* the fitted
    structure, the opposite direction from "the model fits"). `df` is
    the number of non-edges (independence constraints imposed relative
    to the saturated model); a saturated `adjacency` itself has `df=0`,
    for which `p_value` is `nan` (undefined, not a missing value).

    `rmsea`, `cfi`, `tli`, `srmr`: see `docs/decision_log.md`'s D-059
    for the exact formulas. These come with conventional interpretive
    cutoffs in the SEM literature (RMSEA < .05, CFI/TLI > .95,
    SRMR < .08, roughly) that **have not been validated for a sparse
    structure-learning method like GOPC or PC** -- this package
    reports the raw values only, deliberately not a pass/fail
    judgment against those cutoffs.
    """

    chi_square: float
    df: int
    p_value: float
    rmsea: float
    cfi: float
    tli: float
    srmr: float
    target: GGMFitResult
    saturated: GGMFitResult
    null: GGMFitResult


def fit_indices(
    data: np.ndarray,
    adjacency: np.ndarray,
    *,
    ebic_gamma: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> FitIndicesResult:
    """Compute RMSEA, CFI, TLI, and SRMR for `adjacency` against `data`.

    Parameters match `fit_gaussian_graphical_model`'s own (they're
    forwarded to all three internal fits). See that function's own
    docstring for `data`/`adjacency`'s requirements, and
    `docs/decision_log.md`'s D-059 for the formulas and this function's
    explicit choice not to report pass/fail judgments against SEM's
    conventional cutoffs.

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc, fit_indices
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> result = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    >>> indices = fit_indices(data, result.adjacency)
    >>> indices.rmsea, indices.cfi, indices.tli, indices.srmr  # doctest: +SKIP
    """
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("data must be a two-dimensional array")
    n, p = values.shape

    total_pairs = p * (p - 1) // 2

    saturated_adjacency = np.ones((p, p), dtype=bool)
    np.fill_diagonal(saturated_adjacency, False)
    null_adjacency = np.zeros((p, p), dtype=bool)

    target = fit_gaussian_graphical_model(values, adjacency, ebic_gamma=ebic_gamma, max_iter=max_iter, tol=tol)
    saturated = fit_gaussian_graphical_model(
        values, saturated_adjacency, ebic_gamma=ebic_gamma, max_iter=max_iter, tol=tol
    )
    null = fit_gaussian_graphical_model(
        values, null_adjacency, ebic_gamma=ebic_gamma, max_iter=max_iter, tol=tol
    )

    df_target = total_pairs - target.n_edges
    df_null = total_pairs

    chi_square_target = max(0.0, 2.0 * (saturated.log_likelihood - target.log_likelihood))
    chi_square_null = max(0.0, 2.0 * (saturated.log_likelihood - null.log_likelihood))

    p_value = float(_chi2_distribution.sf(chi_square_target, df_target)) if df_target > 0 else float("nan")

    if df_target > 0:
        rmsea = float(np.sqrt(max(chi_square_target - df_target, 0.0) / (df_target * (n - 1))))
    else:
        rmsea = 0.0

    d_target = max(chi_square_target - df_target, 0.0)
    d_null = max(chi_square_null - df_null, 0.0)
    denominator = max(d_target, d_null)
    cfi = 1.0 - d_target / denominator if denominator > 0 else 1.0

    if df_target > 0 and df_null > 0:
        null_ratio = chi_square_null / df_null
        tli_denominator = null_ratio - 1.0
        if tli_denominator != 0:
            tli = float((null_ratio - chi_square_target / df_target) / tli_denominator)
        else:
            tli = float("nan")
    else:
        tli = float("nan")

    sample_covariance = np.cov(values, rowvar=False, ddof=0)
    sample_correlation = _correlation_matrix(sample_covariance)
    fitted_correlation = _correlation_matrix(target.covariance)
    lower_indices = np.tril_indices(p)
    residuals = sample_correlation[lower_indices] - fitted_correlation[lower_indices]
    srmr = float(np.sqrt(np.mean(residuals**2)))

    return FitIndicesResult(
        chi_square=chi_square_target,
        df=df_target,
        p_value=p_value,
        rmsea=rmsea,
        cfi=cfi,
        tli=tli,
        srmr=srmr,
        target=target,
        saturated=saturated,
        null=null,
    )


class _FitResult(Protocol):
    adjacency: np.ndarray


@dataclass(frozen=True)
class TrainTestFitResult:
    """Out-of-sample goodness-of-fit for a structure that was itself
    *discovered* on this data, not specified in advance.

    `adjacency` is the structure `fit` produced from the training
    split only; `in_sample` is `fit_indices(train_data, adjacency)`
    (the same optimistic number a direct `fit_indices(data, adjacency)`
    call would give, for comparison) and `out_of_sample` is
    `fit_indices(test_data, adjacency)` -- the honest number, since the
    test rows played no part in selecting `adjacency`. A large gap
    between the two (out-of-sample fit noticeably worse) is evidence
    that some of the in-sample fit was the structure search fitting
    this particular sample's noise rather than genuine population
    structure; see `docs/decision_log.md`'s D-060.
    """

    adjacency: np.ndarray
    n_train: int
    n_test: int
    in_sample: FitIndicesResult
    out_of_sample: FitIndicesResult


def train_test_fit_indices(
    data: np.ndarray,
    fit: Callable[[np.ndarray], _FitResult],
    *,
    test_proportion: float = 0.5,
    ebic_gamma: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-6,
    rng: np.random.Generator,
) -> TrainTestFitResult:
    """Split `data` by row into a train/test partition, run `fit` on
    the training split only, and report `fit_indices` for the
    resulting structure against both splits.

    Parameters
    ----------
    data : np.ndarray
        ``(n_samples, n_variables)`` array of continuous, approximately
        Gaussian observations.
    fit : Callable[[np.ndarray], _FitResult]
        Any of this package's four fit functions, with its own
        hyperparameters already bound (`functools.partial` or a
        lambda) -- the same convention `bootstrap_edge_stability` and
        friends use. Called once, on the training split.
    test_proportion : float, default 0.5
        Fraction of rows (rounded) held out for the test split; the
        remainder is the training split. Must leave at least one row
        on each side, and both splits must have more rows than
        `data` has columns for `fit_gaussian_graphical_model`'s
        sample covariance to be invertible.
    ebic_gamma, max_iter, tol : forwarded to `fit_indices` for both
        splits.
    rng : np.random.Generator
        Controls the train/test row assignment.

    Returns
    -------
    TrainTestFitResult

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc, train_test_fit_indices
    >>> from functools import partial
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=1000)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=1000)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=1000)
    >>> data = np.column_stack([x1, x2, x3])
    >>> fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)
    >>> result = train_test_fit_indices(data, fit, rng=np.random.default_rng(1))
    >>> result.in_sample.rmsea, result.out_of_sample.rmsea  # doctest: +SKIP
    """
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("data must be a two-dimensional array")
    n = values.shape[0]
    if not (0.0 < test_proportion < 1.0):
        raise ValueError("test_proportion must be in (0, 1)")

    n_test = round(test_proportion * n)
    n_train = n - n_test
    if n_test < 1 or n_train < 1:
        raise ValueError("test_proportion leaves no rows on one side of the split")

    permutation = rng.permutation(n)
    test_rows = values[permutation[:n_test]]
    train_rows = values[permutation[n_test:]]

    fitted = fit(train_rows)
    adjacency = np.asarray(fitted.adjacency)

    in_sample = fit_indices(train_rows, adjacency, ebic_gamma=ebic_gamma, max_iter=max_iter, tol=tol)
    out_of_sample = fit_indices(test_rows, adjacency, ebic_gamma=ebic_gamma, max_iter=max_iter, tol=tol)

    return TrainTestFitResult(
        adjacency=adjacency,
        n_train=n_train,
        n_test=n_test,
        in_sample=in_sample,
        out_of_sample=out_of_sample,
    )
