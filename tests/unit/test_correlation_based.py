import numpy as np
import pytest

from gopcnet.dpi.correlation_based import partial_correlation_from_corr, partial_correlation_test_from_corr
from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence


def _correlated_data(n: int, p: int, rng: np.random.Generator) -> np.ndarray:
    a = rng.normal(size=(p, p)) * (rng.random((p, p)) < 0.4)
    covariance = a @ a.T + np.eye(p)
    return rng.standard_normal((n, p)) @ np.linalg.cholesky(covariance).T


@pytest.mark.parametrize("n", [50, 300, 2000])
def test_matches_frozen_residual_primitive(n: int) -> None:
    """Numerical equivalence with the frozen primitive every archived
    result used, across sample sizes and conditioning-set sizes 0-4."""
    rng = np.random.default_rng(n)
    p = 8
    for _ in range(50):
        data = _correlated_data(n, p, rng)
        corr = np.corrcoef(data, rowvar=False)
        i, j = rng.choice(p, size=2, replace=False)
        others = [k for k in range(p) if k not in (i, j)]
        size = int(rng.integers(0, 5))
        conditioning = sorted(rng.choice(others, size=size, replace=False).tolist())

        frozen = compute_partial_correlation_evidence(data, int(i), int(j), conditioning)
        fast = partial_correlation_test_from_corr(corr, n, int(i), int(j), conditioning)

        assert fast.partial_correlation == pytest.approx(frozen.partial_correlation, abs=1e-10)
        assert fast.z_statistic == pytest.approx(frozen.z_statistic, abs=1e-8)
        assert fast.p_value == pytest.approx(frozen.p_value, rel=1e-8, abs=1e-15)


def test_zero_order_is_the_correlation_itself() -> None:
    corr = np.array([[1.0, 0.4, 0.2], [0.4, 1.0, 0.1], [0.2, 0.1, 1.0]])

    assert partial_correlation_from_corr(corr, 0, 1, []) == 0.4


def test_first_order_matches_closed_form() -> None:
    r01, r02, r12 = 0.5, 0.4, 0.3
    corr = np.array([[1.0, r01, r02], [r01, 1.0, r12], [r02, r12, 1.0]])
    expected = (r01 - r02 * r12) / np.sqrt((1 - r02**2) * (1 - r12**2))

    assert partial_correlation_from_corr(corr, 0, 1, [2]) == pytest.approx(expected, abs=1e-14)


def test_nonpositive_degrees_of_freedom_raise() -> None:
    corr = np.eye(6)
    with pytest.raises(ValueError, match="not enough rows"):
        partial_correlation_test_from_corr(corr, 6, 0, 1, [2, 3, 4])


def test_singular_conditioning_submatrix_raises() -> None:
    corr = np.array(
        [
            [1.0, 0.3, 0.5, 0.5],
            [0.3, 1.0, 0.2, 0.2],
            [0.5, 0.2, 1.0, 1.0],  # column 3 duplicates column 2
            [0.5, 0.2, 1.0, 1.0],
        ]
    )
    with pytest.raises(ValueError, match="singular"):
        partial_correlation_from_corr(corr, 0, 1, [2, 3])


def test_se_scale_divides_z() -> None:
    corr = np.array([[1.0, 0.3, 0.2], [0.3, 1.0, 0.1], [0.2, 0.1, 1.0]])

    base = partial_correlation_test_from_corr(corr, 500, 0, 1, [2])
    scaled = partial_correlation_test_from_corr(corr, 500, 0, 1, [2], se_scale=2.0)

    assert scaled.z_statistic == pytest.approx(base.z_statistic / 2.0)
    assert scaled.p_value > base.p_value


@pytest.mark.parametrize("i, j, conditioning", [(0, 0, []), (0, 1, [1]), (0, 1, [2, 2]), (0, 5, []), (0, 1, [-1])])
def test_invalid_indices_raise(i: int, j: int, conditioning: list[int]) -> None:
    with pytest.raises(ValueError):
        partial_correlation_from_corr(np.eye(3), i, j, conditioning)


def test_nonpositive_se_scale_raises() -> None:
    with pytest.raises(ValueError, match="se_scale"):
        partial_correlation_test_from_corr(np.eye(3), 100, 0, 1, [], se_scale=0.0)
