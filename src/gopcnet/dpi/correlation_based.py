"""Partial-correlation tests computed from a correlation matrix and a
sample size, rather than from raw data.

`gopcnet.dpi.multi_conditional.compute_partial_correlation_evidence` (the
frozen primitive every archived result used) residualizes the raw data by
OLS for every single test, which costs `O(N * k^2)` per test. The partial
correlation of `i` and `j` given `S` depends only on the correlation
submatrix over `A = [i, j, *S]`: with `Q = inv(R[A][:, A])`,

    pcor(i, j | S) = -Q[0, 1] / sqrt(Q[0, 0] * Q[1, 1])

For Pearson correlations this equals the residual-based value exactly in
exact arithmetic (the frozen primitive's OLS includes an intercept, and
Pearson correlation centers the data). Each test is then an inversion of
at most a 6 x 6 matrix at the default conditioning cap, independent of
`N`. It also accepts any other correlation estimate (e.g. rank-based or
polychoric), which is what ordinal-data support will build on
(`docs/development_plan/phase3_ordinal.md`).

The frozen primitive is not modified. Equivalence is pinned by
`tests/unit/test_correlation_based.py`.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.stats import norm

from gopcnet.dpi.multi_conditional import PartialCorrelationEvidence

# A conditioning submatrix whose condition number exceeds this is treated as
# numerically singular: the test is inconclusive (ValueError), the same way the
# frozen primitive treats a (near-)collinear conditioning set.
CONDITION_NUMBER_LIMIT = 1e10


def _validate_indices(p: int, i: int, j: int, conditioning: Sequence[int]) -> list[int]:
    conditioning = [int(c) for c in conditioning]
    if i == j or i in conditioning or j in conditioning:
        raise ValueError("i, j, and conditioning must all be distinct columns")
    if len(set(conditioning)) != len(conditioning):
        raise ValueError("i, j, and conditioning must all be distinct columns")
    if not (0 <= i < p and 0 <= j < p) or any(not (0 <= c < p) for c in conditioning):
        raise ValueError("i, j, and conditioning must be valid column indices")
    return conditioning


def partial_correlation_from_corr(corr: np.ndarray, i: int, j: int, conditioning: Sequence[int]) -> float:
    """Partial correlation of variables `i` and `j` given `conditioning`,
    from a correlation matrix. Raises `ValueError` if the relevant
    submatrix is numerically singular."""
    matrix = np.asarray(corr, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("corr must be a square matrix")
    conditioning = _validate_indices(matrix.shape[0], i, j, conditioning)
    if not conditioning:
        r = float(matrix[i, j])
    else:
        index = [i, j, *conditioning]
        sub = matrix[np.ix_(index, index)]
        condition_number = np.linalg.cond(sub)
        if not np.isfinite(condition_number) or condition_number > CONDITION_NUMBER_LIMIT:
            raise ValueError(
                "conditioning submatrix is numerically singular (perfect collinearity); "
                "partial correlation is undefined"
            )
        precision = np.linalg.inv(sub)
        r = float(-precision[0, 1] / np.sqrt(precision[0, 0] * precision[1, 1]))
    if not np.isfinite(r):
        raise ValueError("partial correlation is undefined for this input (non-finite result)")
    return r


def partial_correlation_test_from_corr(
    corr: np.ndarray,
    n: int,
    i: int,
    j: int,
    conditioning: Sequence[int],
    *,
    se_scale: float = 1.0,
) -> PartialCorrelationEvidence:
    """Fisher-z test of `pcor(i, j | conditioning) = 0`, from a correlation
    matrix and sample size `n`.

    `z = arctanh(r) * sqrt(n - 3 - |S|) / se_scale`, two-sided p-value.
    `se_scale = 1` is the exact Gaussian/Pearson case and reproduces the
    frozen residual-based primitive. A larger `se_scale` widens the
    standard error, e.g. for noisier correlation estimates.

    Raises `ValueError` (which callers treat as "inconclusive", exactly
    as with the frozen primitive) when the degrees of freedom are not
    positive, the indices are invalid, or the conditioning submatrix is
    numerically singular.
    """
    if se_scale <= 0:
        raise ValueError("se_scale must be positive")
    degrees_of_freedom = int(n) - 3 - len(conditioning)
    if degrees_of_freedom <= 0:
        raise ValueError("not enough rows for this conditioning set size")
    r = partial_correlation_from_corr(corr, i, j, conditioning)
    r = float(np.clip(r, -1.0 + 1e-12, 1.0 - 1e-12))
    z = float(np.arctanh(r) * np.sqrt(degrees_of_freedom) / se_scale)
    p_value = float(2.0 * norm.sf(abs(z)))
    return PartialCorrelationEvidence(r, z, p_value)
