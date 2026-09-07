from functools import partial

import numpy as np
import pytest

from gopcnet import fit_ebicglasso, fit_gopc, strength
from gopcnet.stability import (
    CaseDropResult,
    CSCoefficientResult,
    case_drop_bootstrap,
    case_drop_resample,
    cs_coefficient,
)


def _chain_data(seed: int, n: int = 600) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.7 * x1 + np.sqrt(1 - 0.7**2) * rng.normal(size=n)
    x3 = 0.7 * x2 + np.sqrt(1 - 0.7**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_case_drop_resample_draws_without_replacement() -> None:
    data = np.arange(20).reshape(20, 1).astype(float)  # each row uniquely identifiable by its value
    resample = case_drop_resample(data, 10, np.random.default_rng(0))
    assert resample.shape == (10, 1)
    assert len(set(resample[:, 0].tolist())) == 10  # no duplicates


def test_case_drop_resample_rejects_invalid_n_keep() -> None:
    data = np.zeros((10, 2))
    with pytest.raises(ValueError):
        case_drop_resample(data, 0, np.random.default_rng(0))
    with pytest.raises(ValueError):
        case_drop_resample(data, 11, np.random.default_rng(0))


def test_case_drop_bootstrap_tallies_successful_and_failed_per_proportion() -> None:
    data = _chain_data(0)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    result = case_drop_bootstrap(
        data,
        fit,
        lambda r: strength(r.weights),
        proportions_retained=(0.9, 0.5),
        bootstraps_per_proportion=8,
        rng=np.random.default_rng(1),
    )

    assert isinstance(result, CaseDropResult)
    assert result.full_sample_statistic.shape == (3,)
    for p in (0.9, 0.5):
        assert result.successful[p] + result.failed[p] == 8
        assert result.replicate_statistics[p].shape[0] == result.successful[p]
        if result.successful[p] > 0:
            assert result.replicate_statistics[p].shape[1] == 3


def test_case_drop_bootstrap_works_with_a_method_that_has_no_weights() -> None:
    """fit_ebicglasso has no .weights -- the statistic function must be
    free to use whatever the result does expose (here, node degree)."""
    data = _chain_data(0)

    result = case_drop_bootstrap(
        data,
        fit_ebicglasso,
        lambda r: r.adjacency.sum(axis=1).astype(float),
        proportions_retained=(0.9,),
        bootstraps_per_proportion=5,
        rng=np.random.default_rng(2),
    )

    assert result.full_sample_statistic.shape == (3,)
    assert result.successful[0.9] + result.failed[0.9] == 5


def test_case_drop_bootstrap_rejects_empty_proportions() -> None:
    data = _chain_data(0)
    with pytest.raises(ValueError):
        case_drop_bootstrap(
            data, fit_ebicglasso, lambda r: r.adjacency.sum(axis=1).astype(float),
            proportions_retained=(), bootstraps_per_proportion=5, rng=np.random.default_rng(0),
        )


def test_case_drop_bootstrap_rejects_out_of_range_proportions() -> None:
    data = _chain_data(0)
    with pytest.raises(ValueError):
        case_drop_bootstrap(
            data, fit_ebicglasso, lambda r: r.adjacency.sum(axis=1).astype(float),
            proportions_retained=(1.5,), bootstraps_per_proportion=5, rng=np.random.default_rng(0),
        )


def test_cs_coefficient_finds_the_largest_monotonically_valid_drop_proportion() -> None:
    """Constructed, deterministic replicate statistics -- p=0.9 and
    p=0.7 perfectly match the full-sample ranking (pass), p=0.5 is
    perfectly reversed (fail) -- so the CS-coefficient must stop at the
    last passing level (drop = 1 - 0.7 = 0.3), not skip over the
    failure to a coincidentally-passing lower level."""
    full_stat = np.array([1.0, 2.0, 3.0, 4.0])
    perfect = np.tile(full_stat, (10, 1))
    reversed_stat = np.array([4.0, 3.0, 2.0, 1.0])
    anti_correlated = np.tile(reversed_stat, (10, 1))

    result = CaseDropResult(
        full_sample_statistic=full_stat,
        replicate_statistics={0.9: perfect, 0.7: perfect, 0.5: anti_correlated},
        successful={0.9: 10, 0.7: 10, 0.5: 10},
        failed={0.9: 0, 0.7: 0, 0.5: 0},
    )

    result_cs = cs_coefficient(result, correlation_threshold=0.7, pass_rate_threshold=0.95)

    assert isinstance(result_cs, CSCoefficientResult)
    assert result_cs.cs_coefficient == pytest.approx(0.3)
    assert result_cs.pass_rate_by_proportion_retained[0.9] == 1.0
    assert result_cs.pass_rate_by_proportion_retained[0.7] == 1.0
    assert result_cs.pass_rate_by_proportion_retained[0.5] == 0.0


def test_cs_coefficient_is_zero_when_even_the_least_dropped_level_fails() -> None:
    full_stat = np.array([1.0, 2.0, 3.0, 4.0])
    reversed_stat = np.array([4.0, 3.0, 2.0, 1.0])
    anti_correlated = np.tile(reversed_stat, (10, 1))

    result = CaseDropResult(
        full_sample_statistic=full_stat,
        replicate_statistics={0.9: anti_correlated},
        successful={0.9: 10},
        failed={0.9: 0},
    )

    result_cs = cs_coefficient(result)
    assert result_cs.cs_coefficient == 0.0


def test_cs_coefficient_treats_nan_correlation_as_failing_not_crashing() -> None:
    """A replicate whose statistic vector has zero variance produces a
    NaN Spearman correlation -- must count as not meeting the
    threshold, not raise or silently pass."""
    full_stat = np.array([1.0, 2.0, 3.0, 4.0])
    constant = np.tile(np.array([5.0, 5.0, 5.0, 5.0]), (5, 1))

    result = CaseDropResult(
        full_sample_statistic=full_stat,
        replicate_statistics={0.9: constant},
        successful={0.9: 5},
        failed={0.9: 0},
    )

    result_cs = cs_coefficient(result)
    assert result_cs.pass_rate_by_proportion_retained[0.9] == 0.0
    assert result_cs.cs_coefficient == 0.0


def test_cs_coefficient_treats_no_successful_replicates_as_failing() -> None:
    result = CaseDropResult(
        full_sample_statistic=np.array([1.0, 2.0]),
        replicate_statistics={0.9: np.empty((0, 2))},
        successful={0.9: 0},
        failed={0.9: 5},
    )
    result_cs = cs_coefficient(result)
    assert result_cs.pass_rate_by_proportion_retained[0.9] == 0.0
    assert result_cs.cs_coefficient == 0.0


def test_cs_coefficient_rejects_invalid_thresholds() -> None:
    result = CaseDropResult(
        full_sample_statistic=np.array([1.0, 2.0]),
        replicate_statistics={0.9: np.array([[1.0, 2.0]])},
        successful={0.9: 1},
        failed={0.9: 0},
    )
    with pytest.raises(ValueError):
        cs_coefficient(result, correlation_threshold=0.0)
    with pytest.raises(ValueError):
        cs_coefficient(result, pass_rate_threshold=1.5)


def test_end_to_end_case_drop_and_cs_coefficient_on_a_well_determined_network() -> None:
    """A large-N, strongly-connected chain should be reasonably stable
    -- not asserting an exact CS value (that depends on the RNG draw),
    just that the pipeline runs end-to-end and produces a coefficient
    in the valid [0, 1] range."""
    data = _chain_data(0, n=800)
    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

    case_drop = case_drop_bootstrap(
        data,
        fit,
        lambda r: strength(r.weights),
        bootstraps_per_proportion=15,
        rng=np.random.default_rng(3),
    )
    result_cs = cs_coefficient(case_drop)

    assert 0.0 <= result_cs.cs_coefficient <= 1.0
