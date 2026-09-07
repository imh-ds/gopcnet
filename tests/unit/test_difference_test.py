from functools import partial

import numpy as np
import pytest

from gopcnet import fit_gopc, strength
from gopcnet.stability import (
    BootstrapReplicates,
    DifferenceTestResult,
    bootstrap_replicates,
    difference_test,
)


def _chain_data(seed: int, n: int = 500) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def _replicates(full: np.ndarray, rows: np.ndarray) -> BootstrapReplicates:
    return BootstrapReplicates(
        full_sample_statistic=full, replicate_statistics=rows, successful=rows.shape[0], failed=0
    )


def test_difference_test_reports_the_full_sample_point_estimate() -> None:
    full = np.array([5.0, 2.0])
    rows = np.tile(np.array([5.0, 2.0]), (20, 1))
    result = difference_test(_replicates(full, rows), 0, 1)
    assert result.difference == pytest.approx(3.0)


def test_difference_test_is_significant_when_ci_excludes_zero() -> None:
    full = np.array([5.0, 2.0])
    rng = np.random.default_rng(0)
    # replicate differences all clustered well above zero (mean ~3, small noise)
    a = 5.0 + rng.normal(scale=0.1, size=200)
    b = 2.0 + rng.normal(scale=0.1, size=200)
    rows = np.column_stack([a, b])

    result = difference_test(_replicates(full, rows), 0, 1)

    assert isinstance(result, DifferenceTestResult)
    assert result.ci_low > 0.0
    assert result.significant is True


def test_difference_test_is_not_significant_when_ci_straddles_zero() -> None:
    full = np.array([1.0, 1.0])
    rng = np.random.default_rng(1)
    # both entries drawn from the same noisy distribution -> difference centered on 0
    a = rng.normal(loc=1.0, scale=1.0, size=200)
    b = rng.normal(loc=1.0, scale=1.0, size=200)
    rows = np.column_stack([a, b])

    result = difference_test(_replicates(full, rows), 0, 1)

    assert result.ci_low < 0.0 < result.ci_high
    assert result.significant is False


def test_difference_test_rejects_invalid_alpha() -> None:
    full = np.array([1.0, 2.0])
    rows = np.tile(full, (5, 1))
    with pytest.raises(ValueError):
        difference_test(_replicates(full, rows), 0, 1, alpha=0.0)
    with pytest.raises(ValueError):
        difference_test(_replicates(full, rows), 0, 1, alpha=1.0)


def test_difference_test_rejects_out_of_range_indices() -> None:
    full = np.array([1.0, 2.0])
    rows = np.tile(full, (5, 1))
    with pytest.raises(ValueError):
        difference_test(_replicates(full, rows), 0, 5)
    with pytest.raises(ValueError):
        difference_test(_replicates(full, rows), -1, 1)


def test_difference_test_rejects_identical_indices() -> None:
    full = np.array([1.0, 2.0])
    rows = np.tile(full, (5, 1))
    with pytest.raises(ValueError):
        difference_test(_replicates(full, rows), 0, 0)


def test_bootstrap_replicates_tallies_successful_and_failed() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    result = bootstrap_replicates(
        data, fit, lambda r: strength(r.weights), bootstraps=20, rng=np.random.default_rng(2)
    )

    assert isinstance(result, BootstrapReplicates)
    assert result.full_sample_statistic.shape == (3,)
    assert result.replicate_statistics.shape == (result.successful, 3)
    assert result.successful + result.failed == 20


def test_bootstrap_replicates_raises_when_every_resample_fails() -> None:
    """The full-sample statistic call must succeed (it's not a resample,
    so failing there is a real error, not "every bootstrap failed") --
    only the resampled calls are made to fail here."""
    data = _chain_data(0)

    def fit_full_sample_only(candidate: np.ndarray) -> np.ndarray:
        if candidate is data:
            return candidate
        raise ValueError("degenerate resample by construction")

    with pytest.raises(RuntimeError):
        bootstrap_replicates(
            data, fit_full_sample_only, lambda r: r.sum(axis=0), bootstraps=5, rng=np.random.default_rng(3)
        )


def test_end_to_end_difference_test_on_real_fit_gopc_strength() -> None:
    data = _chain_data(0, n=700)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    replicates = bootstrap_replicates(
        data, fit, lambda r: strength(r.weights), bootstraps=60, rng=np.random.default_rng(4)
    )
    result = difference_test(replicates, 0, 2)  # endpoints of the chain: both weakly connected

    assert result.ci_low <= result.ci_high
    assert result.difference == pytest.approx(
        replicates.full_sample_statistic[0] - replicates.full_sample_statistic[2]
    )
