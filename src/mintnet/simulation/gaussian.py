"""Gaussian data-generating processes with analytic MI ground truth."""

import math

import numpy as np


def _validate_rho(rho: float) -> float:
    """Return a valid correlation as a float."""
    value = float(rho)
    if not -1.0 < value < 1.0:
        raise ValueError("rho must satisfy -1 < rho < 1")
    return value


def gaussian_mi(rho: float) -> float:
    """Return bivariate Gaussian mutual information in nats."""
    value = _validate_rho(rho)
    return -0.5 * math.log1p(-(value * value))


def sample_bivariate_gaussian(
    n: int, rho: float, rng: np.random.Generator
) -> np.ndarray:
    """Draw ``n`` observations from a unit-variance bivariate Gaussian."""
    if n < 1:
        raise ValueError("n must be at least 1")
    value = _validate_rho(rho)
    covariance = np.array([[1.0, value], [value, 1.0]])
    return rng.multivariate_normal(mean=np.zeros(2), cov=covariance, size=n)
