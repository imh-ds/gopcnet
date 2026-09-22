"""Non-regularized Gaussian graphical model: full-order partial
correlations, each tested, with multiple-testing control.

In network psychometrics this is the usual alternative to EBICglasso
when specificity matters: estimate every partial correlation from the
inverse sample correlation matrix (each conditioned on *all* other
variables), test each with a Fisher-z test, and control the error rate
across all `p(p - 1)/2` pairs. See, e.g., Williams & Rast (2020,
"Back to the basics", British Journal of Mathematical and Statistical
Psychology) and Williams, Rhemtulla, Wysocki & Rast (2019,
Multivariate Behavioral Research); the `GGMnonreg` R package implements
the same idea. The citations are recorded for orientation and must be
verified before they are cited in the manuscript.

A comparator only. Like `fit_ebicglasso` and `fit_pc_skeleton`, it is
never mixed into the GOPC pipeline. Added for Stage 7b
(`docs/development_plan/phase1_external_validity.md`, step 1.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import norm

from gopcnet.screening import ScreeningEvidence, benjamini_hochberg_threshold

Correction = Literal["holm", "bh", "none"]


@dataclass(frozen=True)
class NonregularizedResult:
    """Full-order partial-correlation network.

    - `adjacency`: the pairs that survived the multiple-testing
      correction.
    - `weights`: full-order partial correlations, zero off-adjacency.
    - `partial_correlations`: every full-order partial correlation,
      unthresholded.
    - `p_values`: two-sided Fisher-z p-values (one on the diagonal).
    """

    adjacency: np.ndarray
    weights: np.ndarray
    partial_correlations: np.ndarray
    p_values: np.ndarray
    correction: str
    alpha: float


def _full_order_partial_correlations(corr: np.ndarray) -> np.ndarray:
    precision = np.linalg.inv(corr)
    scale = np.sqrt(np.diag(precision))
    partial = -precision / np.outer(scale, scale)
    np.fill_diagonal(partial, 0.0)
    return (partial + partial.T) / 2.0


def _holm(p_values: np.ndarray, alpha: float) -> np.ndarray:
    """Holm step-down: sort ascending; reject while p_(k) <= alpha / (m - k + 1)."""
    m = len(p_values)
    keep = np.zeros(m, dtype=bool)
    for rank, index in enumerate(np.argsort(p_values, kind="stable")):
        if p_values[index] <= alpha / (m - rank):
            keep[index] = True
        else:
            break
    return keep


def fit_nonregularized_ggm_from_correlation(
    corr: np.ndarray,
    n: int,
    *,
    alpha: float = 0.05,
    correction: Correction = "holm",
    se_scale: float = 1.0,
) -> NonregularizedResult:
    """Full-order partial-correlation network from a correlation matrix.

    Each pair is tested conditional on all other `p - 2` variables with
    `z = arctanh(pcor) * sqrt(n - p - 1) / se_scale`, then filtered at
    level `alpha` with `correction`:

    - `"holm"`: family-wise error control
    - `"bh"`: Benjamini-Hochberg false-discovery-rate control
    - `"none"`: every pair tested at `alpha` separately
    """
    matrix = np.asarray(corr, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("corr must be a square matrix")
    p = matrix.shape[0]
    if int(n) != n or n <= p + 1:
        raise ValueError("n must exceed p + 1 for full-order partial correlations")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    if correction not in ("holm", "bh", "none"):
        raise ValueError('correction must be "holm", "bh", or "none"')
    if se_scale <= 0:
        raise ValueError("se_scale must be positive")
    if not np.isfinite(np.linalg.cond(matrix)) or np.linalg.cond(matrix) > 1e12:
        raise ValueError("correlation matrix is numerically singular")

    partial = _full_order_partial_correlations(matrix)
    clipped = np.clip(partial, -1.0 + 1e-12, 1.0 - 1e-12)
    z = np.arctanh(clipped) * np.sqrt(n - p - 1) / se_scale
    p_values = 2.0 * norm.sf(np.abs(z))
    np.fill_diagonal(p_values, 1.0)

    rows, cols = np.triu_indices(p, k=1)
    if correction == "holm":
        keep = _holm(p_values[rows, cols], alpha)
        adjacency = np.zeros((p, p), dtype=bool)
        adjacency[rows, cols] = keep
        adjacency = adjacency | adjacency.T
    elif correction == "bh":
        evidence = ScreeningEvidence(correlation=partial, z_statistic=z, p_value=p_values)
        adjacency = benjamini_hochberg_threshold(evidence, alpha)
    else:
        adjacency = p_values <= alpha
        np.fill_diagonal(adjacency, False)

    weights = np.where(adjacency, partial, 0.0)
    return NonregularizedResult(
        adjacency=adjacency,
        weights=weights,
        partial_correlations=partial,
        p_values=p_values,
        correction=correction,
        alpha=float(alpha),
    )


def fit_nonregularized_ggm(
    data: np.ndarray, *, alpha: float = 0.05, correction: Correction = "holm"
) -> NonregularizedResult:
    """Full-order partial-correlation network from raw data (Pearson
    correlation); see `fit_nonregularized_ggm_from_correlation`."""
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("data must be a two-dimensional array")
    return fit_nonregularized_ggm_from_correlation(
        np.corrcoef(values, rowvar=False), values.shape[0], alpha=alpha, correction=correction
    )
