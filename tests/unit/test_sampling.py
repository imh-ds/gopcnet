import numpy as np
import pytest

from gopcnet.generators import cholesky_factor, covariance_from_precision, sample_gaussian


def _random_covariance(p: int, rng: np.random.Generator) -> np.ndarray:
    a = rng.normal(size=(p, p))
    return a @ a.T + p * np.eye(p)


def test_sample_gaussian_is_deterministic_for_a_seed() -> None:
    covariance = _random_covariance(5, np.random.default_rng(0))

    first = sample_gaussian(covariance, 100, np.random.default_rng(42))
    second = sample_gaussian(covariance, 100, np.random.default_rng(42))

    assert np.array_equal(first, second)


def test_sample_gaussian_recovers_covariance_at_large_n() -> None:
    covariance = _random_covariance(5, np.random.default_rng(1))
    covariance = covariance / np.sqrt(np.outer(np.diag(covariance), np.diag(covariance)))

    draws = sample_gaussian(covariance, 200_000, np.random.default_rng(2))

    assert np.allclose(np.cov(draws, rowvar=False), covariance, atol=0.02)


def test_repeated_eigenvalue_covariance_samples_reproducibly() -> None:
    """The D-065 case: the `overlap` shape's precision has a repeated
    eigenvalue, so its covariance does too. Cholesky has no rotational
    freedom there, so the draw is a fixed function of the seed."""
    precision = np.eye(5)
    for i, j in ((0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4)):
        precision[i, j] = precision[j, i] = -0.25
    covariance = covariance_from_precision(precision)
    eigenvalues = np.linalg.eigvalsh(covariance)
    assert np.min(np.abs(np.diff(np.sort(eigenvalues)))) < 1e-9  # the degeneracy is really there

    first = sample_gaussian(covariance, 500, np.random.default_rng(7))
    second = sample_gaussian(covariance, 500, np.random.default_rng(7))

    assert np.array_equal(first, second)
    assert np.allclose(cholesky_factor(covariance) @ cholesky_factor(covariance).T, covariance)


def test_covariance_from_precision_is_symmetric_inverse() -> None:
    precision = _random_covariance(4, np.random.default_rng(3))

    covariance = covariance_from_precision(precision)

    assert np.array_equal(covariance, covariance.T)
    assert np.allclose(covariance @ precision, np.eye(4), atol=1e-10)


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[1.0, 2.0], [2.0, 1.0]]),  # symmetric, not positive definite
        np.array([[1.0, 0.5], [0.4, 1.0]]),  # asymmetric
        np.ones((2, 3)),  # not square
        np.array([[1.0, np.nan], [np.nan, 1.0]]),  # non-finite
    ],
)
def test_invalid_covariance_raises_value_error(matrix: np.ndarray) -> None:
    with pytest.raises(ValueError):
        sample_gaussian(matrix, 10, np.random.default_rng(0))


@pytest.mark.parametrize("n", [0, -1, 2.5])
def test_invalid_n_raises_value_error(n: float) -> None:
    with pytest.raises(ValueError):
        sample_gaussian(np.eye(2), n, np.random.default_rng(0))  # type: ignore[arg-type]
