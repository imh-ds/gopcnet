"""Gaussian three-node motifs used by the Stage 1 DPI experiment."""

from __future__ import annotations

import numpy as np


_TRIANGLE_PRECISIONS: dict[str, np.ndarray] = {
    "balanced": np.array(
        [[1.0, -0.25, -0.25], [-0.25, 1.0, -0.25], [-0.25, -0.25, 1.0]]
    ),
    "moderate": np.array(
        [[1.0, -0.35, -0.25], [-0.35, 1.0, -0.12], [-0.25, -0.12, 1.0]]
    ),
    "strong": np.array(
        [[1.0, -0.45, -0.25], [-0.45, 1.0, -0.08], [-0.25, -0.08, 1.0]]
    ),
}


def _validate_n(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("n must be at least 1")
    return int(n)


def _validate_strength(strength: float) -> float:
    value = float(strength)
    if not 0.0 < value < 1.0:
        raise ValueError("strength must satisfy 0 < strength < 1")
    return value


def sample_chain(n: int, strength: float, rng: np.random.Generator) -> np.ndarray:
    """Draw a unit-variance Gaussian chain ``X1 -> X2 -> X3``."""
    n = _validate_n(n)
    strength = _validate_strength(strength)
    x1 = rng.normal(size=n)
    x2 = strength * x1 + np.sqrt(1.0 - strength**2) * rng.normal(size=n)
    x3 = strength * x2 + np.sqrt(1.0 - strength**2) * rng.normal(size=n)
    return np.column_stack((x1, x2, x3))


def sample_measured_fork(
    n: int, strength: float, rng: np.random.Generator
) -> np.ndarray:
    """Draw a unit-variance Gaussian fork with latent center ``X2``."""
    n = _validate_n(n)
    strength = _validate_strength(strength)
    x2 = rng.normal(size=n)
    x1 = strength * x2 + np.sqrt(1.0 - strength**2) * rng.normal(size=n)
    x3 = strength * x2 + np.sqrt(1.0 - strength**2) * rng.normal(size=n)
    return np.column_stack((x1, x2, x3))


def sample_hub(n: int, strength: float, children: int, rng: np.random.Generator) -> np.ndarray:
    """Draw a unit-variance Gaussian hub with a shared cause and independent children.

    Column 0 is the hub; columns 1..children are its children, each an
    independent noisy copy of the hub at the given strength. The
    direct three-or-more-child generalization of sample_measured_fork's
    two-child case.
    """
    n = _validate_n(n)
    strength = _validate_strength(strength)
    if not isinstance(children, int) or children < 2:
        raise ValueError("children must be an integer at least 2")
    hub = rng.normal(size=n)
    columns = [hub]
    for _ in range(children):
        columns.append(strength * hub + np.sqrt(1.0 - strength**2) * rng.normal(size=n))
    return np.column_stack(columns)


def triangle_precisions() -> dict[str, np.ndarray]:
    """Return copies of the named positive-definite precision fixtures."""
    return {name: precision.copy() for name, precision in _TRIANGLE_PRECISIONS.items()}


def sample_precision_triangle(
    name: str, n: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw and sample-standardize a Gaussian triangle fixture."""
    n = _validate_n(n)
    try:
        precision = _TRIANGLE_PRECISIONS[name]
    except KeyError as exc:
        raise ValueError(f"unknown triangle precision fixture: {name}") from exc
    try:
        np.linalg.cholesky(precision)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"triangle precision is not positive definite: {name}") from exc
    covariance = np.linalg.inv(precision)
    data = rng.multivariate_normal(np.zeros(3), covariance, size=n)
    return (data - data.mean(axis=0)) / data.std(axis=0, ddof=1)
