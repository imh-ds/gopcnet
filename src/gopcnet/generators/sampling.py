"""Reproducible multivariate-normal sampling for DGPs added after D-065.

Every data-generating process added after D-065 draws through this
module, never through `numpy.random.Generator.multivariate_normal`.
That function factors the covariance by SVD, and when the covariance
has a repeated singular value (the `overlap` DGP's does, at `0.8`,
twice) the rotation inside that degenerate subspace is not pinned
down: the same seed can yield different, equally valid draws on
different machines. That is the most likely cause of Stage 5i's G1/G2
reproduction failures (`docs/decision_log.md`, D-065).

A Cholesky factor is unique for a positive-definite matrix, so a draw
here is a deterministic function of `(seed, covariance)` on any
machine, up to last-bit floating-point differences in the factor
itself, which do not cascade the way an SVD rotation does.

The frozen samplers in `gopcnet.simulation` are deliberately not
migrated: archived evidence was drawn with them, and changing them
would change what every earlier charter's seeds produce.
"""

from __future__ import annotations

import numpy as np


def cholesky_factor(covariance: np.ndarray) -> np.ndarray:
    """Lower-triangular `L` with `L @ L.T == covariance`.

    Raises `ValueError` if the matrix is not square, not symmetric, or
    not positive definite.
    """
    matrix = np.asarray(covariance, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("covariance must be a square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("covariance must contain only finite values")
    if not np.allclose(matrix, matrix.T, rtol=0.0, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    try:
        return np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as exc:
        raise ValueError("covariance must be positive definite") from exc


def sample_gaussian(covariance: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Draw `n` rows from `N(0, covariance)` as `standard_normal((n, p)) @ L.T`.

    Unlike `gopcnet.simulation`'s frozen samplers, the result is not
    sample-standardized: it is the raw draw, so callers can decide
    whether to standardize.
    """
    if int(n) != n or n < 1:
        raise ValueError("n must be a positive integer")
    factor = cholesky_factor(covariance)
    return rng.standard_normal((int(n), factor.shape[0])) @ factor.T


def covariance_from_precision(precision: np.ndarray) -> np.ndarray:
    """Invert a precision matrix and symmetrize away round-off.

    Raises `ValueError` if the precision matrix is not positive
    definite.
    """
    cholesky_factor(precision)  # validates shape, symmetry, positive definiteness
    covariance = np.linalg.inv(np.asarray(precision, dtype=float))
    return (covariance + covariance.T) / 2.0
