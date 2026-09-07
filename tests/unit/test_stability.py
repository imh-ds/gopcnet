from functools import partial

import numpy as np
import pytest

from gopcnet import fit_ebicglasso, fit_gopc, fit_gopc_fixed_order, fit_pc_skeleton
from gopcnet.stability import EdgeStabilityResult, bootstrap_edge_stability, bootstrap_resample


def _chain_data(seed: int, n: int = 300) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_works_with_fit_gopc_and_reports_weight_stability() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    result = bootstrap_edge_stability(data, fit, bootstraps=25, rng=np.random.default_rng(1))

    assert isinstance(result, EdgeStabilityResult)
    assert result.inclusion_probability.shape == (3, 3)
    assert result.weight_mean is not None
    assert result.weight_std is not None
    assert result.weight_mean.shape == (3, 3)
    assert np.all(result.inclusion_probability >= 0.0) and np.all(result.inclusion_probability <= 1.0)
    assert result.successful_bootstraps + result.failed_bootstraps == 25


def test_works_with_fit_gopc_fixed_order() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc_fixed_order, screening_alpha=0.05, dpi_alpha=0.05)

    result = bootstrap_edge_stability(data, fit, bootstraps=20, rng=np.random.default_rng(2))

    assert result.weight_mean is not None
    assert result.weight_std is not None


def test_comparators_have_no_weight_since_they_dont_define_one() -> None:
    """fit_ebicglasso and fit_pc_skeleton's result objects have no
    .weights attribute (see docs/decision_log.md's D-055) -- weight
    fields must be None, not silently zero or fabricated."""
    data = _chain_data(0)

    ebic_result = bootstrap_edge_stability(
        data, fit_ebicglasso, bootstraps=15, rng=np.random.default_rng(3)
    )
    assert ebic_result.weight_mean is None
    assert ebic_result.weight_std is None

    pc_fit = partial(fit_pc_skeleton, alpha=0.05)
    pc_result = bootstrap_edge_stability(data, pc_fit, bootstraps=15, rng=np.random.default_rng(4))
    assert pc_result.weight_mean is None
    assert pc_result.weight_std is None


def test_rejects_nonpositive_bootstraps() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    with pytest.raises(ValueError):
        bootstrap_edge_stability(data, fit, bootstraps=0, rng=np.random.default_rng(5))


def test_is_reproducible_given_the_same_rng_state() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    result_a = bootstrap_edge_stability(data, fit, bootstraps=15, rng=np.random.default_rng(6))
    result_b = bootstrap_edge_stability(data, fit, bootstraps=15, rng=np.random.default_rng(6))

    assert np.array_equal(result_a.inclusion_probability, result_b.inclusion_probability)
    assert np.allclose(result_a.weight_mean, result_b.weight_mean)


def test_failed_resamples_are_excluded_not_counted_as_edge_absent() -> None:
    """A fit callable that always raises ValueError must not silently
    contribute zeros to inclusion_probability -- every resample should
    be tallied as failed, and the function should refuse to divide by
    zero successful resamples."""
    data = _chain_data(0)

    def always_fails(_: np.ndarray) -> None:
        raise ValueError("degenerate by construction")

    with pytest.raises(RuntimeError):
        bootstrap_edge_stability(data, always_fails, bootstraps=5, rng=np.random.default_rng(7))


def test_partial_failures_are_tallied_separately_from_successes() -> None:
    data = _chain_data(0)
    calls = {"n": 0}

    def fails_every_other_call(resample: np.ndarray):
        calls["n"] += 1
        if calls["n"] % 2 == 0:
            raise ValueError("simulated degenerate resample")
        return fit_gopc(resample, screening_alpha=0.05, dpi_alpha=0.05)

    result = bootstrap_edge_stability(data, fails_every_other_call, bootstraps=10, rng=np.random.default_rng(8))

    assert result.successful_bootstraps == 5
    assert result.failed_bootstraps == 5


def test_bootstrap_resample_preserves_row_count() -> None:
    data = _chain_data(0, n=50)
    resample = bootstrap_resample(data, np.random.default_rng(9))
    assert resample.shape == data.shape
