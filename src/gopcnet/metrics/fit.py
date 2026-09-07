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
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
