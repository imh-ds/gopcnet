from dataclasses import dataclass
from functools import partial

import numpy as np
import pytest

from gopcnet import fit_gopc
from gopcnet.network_comparison import NetworkComparisonResult, network_comparison_test


@dataclass(frozen=True)
class _FakeResult:
    weights: np.ndarray | None


def _weights_fit(matrix: np.ndarray):
    """A deterministic 'fit' whose result depends only on which half of
    the data rows are all-positive vs. all-negative -- lets tests target
    the permutation machinery itself without depending on fit_gopc's own
    statistical behavior."""

    def fit(data: np.ndarray) -> _FakeResult:
        # Deterministic "network": edge weight is the sign of the mean of
        # each pair of columns' product, scaled by a constant -- exercises
        # real numbers without depending on any estimation procedure.
        p = data.shape[1]
        weights = np.zeros((p, p))
        for i in range(p):
            for j in range(i + 1, p):
                value = float(np.mean(data[:, i] * data[:, j]))
                weights[i, j] = weights[j, i] = value
        return _FakeResult(weights=weights)

    return fit


def _chain_data(seed: int, n: int = 300, shift: float = 0.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(loc=shift, size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_returns_network_comparison_result_with_valid_ranges() -> None:
    data_a = _chain_data(0)
    data_b = _chain_data(1)
    fit = _weights_fit(data_a)

    result = network_comparison_test(data_a, data_b, fit, permutations=50, rng=np.random.default_rng(0))

    assert isinstance(result, NetworkComparisonResult)
    assert result.observed_global_strength_difference >= 0.0
    assert result.observed_max_edge_weight_difference >= 0.0
    assert 0.0 < result.global_strength_p_value <= 1.0
    assert 0.0 < result.max_edge_weight_difference_p_value <= 1.0
    assert result.successful_permutations + result.failed_permutations == 50


def test_p_value_is_never_exactly_zero() -> None:
    """Add-one smoothing: even a maximally extreme observed statistic
    should not report p=0."""
    data_a = _chain_data(0)
    data_b = _chain_data(0)  # identical distribution to its own permutations

    def extreme_fit(data: np.ndarray):
        # First call (data_a) gets huge weights; every other call (data_b,
        # and every permutation) gets zero weights -- guarantees the
        # observed difference exceeds every permuted one.
        if extreme_fit.calls == 0:
            extreme_fit.calls += 1
            return _FakeResult(weights=np.array([[0.0, 100.0], [100.0, 0.0]]))
        return _FakeResult(weights=np.zeros((2, 2)))

    extreme_fit.calls = 0
    result = network_comparison_test(
        data_a[:, :2], data_b[:, :2], extreme_fit, permutations=20, rng=np.random.default_rng(0)
    )
    assert result.global_strength_p_value == pytest.approx(1.0 / 21.0)
    assert result.max_edge_weight_difference_p_value == pytest.approx(1.0 / 21.0)


def test_identical_networks_give_zero_observed_difference() -> None:
    data = _chain_data(0)
    fit = _weights_fit(data)
    result = network_comparison_test(data, data.copy(), fit, permutations=30, rng=np.random.default_rng(2))
    assert result.observed_global_strength_difference == pytest.approx(0.0)
    assert result.observed_max_edge_weight_difference == pytest.approx(0.0)


def test_rejects_mismatched_column_counts() -> None:
    data_a = _chain_data(0)
    data_b = _chain_data(1)[:, :2]
    fit = _weights_fit(data_a)
    with pytest.raises(ValueError, match="same number of columns"):
        network_comparison_test(data_a, data_b, fit, permutations=5, rng=np.random.default_rng(0))


def test_rejects_non_positive_permutations() -> None:
    data_a = _chain_data(0)
    data_b = _chain_data(1)
    fit = _weights_fit(data_a)
    with pytest.raises(ValueError, match="permutations"):
        network_comparison_test(data_a, data_b, fit, permutations=0, rng=np.random.default_rng(0))


def test_raises_when_fit_result_has_no_weights() -> None:
    data_a = _chain_data(0)
    data_b = _chain_data(1)

    def unweighted_fit(data: np.ndarray) -> _FakeResult:
        return _FakeResult(weights=None)

    with pytest.raises(ValueError, match="edge weights"):
        network_comparison_test(data_a, data_b, unweighted_fit, permutations=5, rng=np.random.default_rng(0))


def test_raises_when_every_permutation_is_degenerate() -> None:
    data_a = _chain_data(0)
    data_b = _chain_data(1)

    def fit(data: np.ndarray) -> _FakeResult:
        if fit.calls < 2:
            fit.calls += 1
            return _FakeResult(weights=np.zeros((data.shape[1], data.shape[1])))
        raise ValueError("degenerate permuted split by construction")

    fit.calls = 0
    with pytest.raises(RuntimeError):
        network_comparison_test(data_a, data_b, fit, permutations=5, rng=np.random.default_rng(0))


def test_end_to_end_on_real_fit_gopc_two_similar_groups() -> None:
    data_a = _chain_data(10, n=400)
    data_b = _chain_data(11, n=400)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    result = network_comparison_test(data_a, data_b, fit, permutations=40, rng=np.random.default_rng(5))

    assert isinstance(result, NetworkComparisonResult)
    assert result.permutation_global_strength_differences.shape[0] == result.successful_permutations
    assert result.permutation_max_edge_weight_differences.shape[0] == result.successful_permutations
