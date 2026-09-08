from functools import partial

import numpy as np
import pytest

from gopcnet import fit_gopc
from gopcnet.metrics.fit import FitIndicesResult, TrainTestFitResult, train_test_fit_indices


def _chain_data(seed: int, n: int = 1000) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def _fit():
    return partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)


def test_returns_train_test_fit_result_with_sane_splits() -> None:
    data = _chain_data(0)
    result = train_test_fit_indices(data, _fit(), test_proportion=0.3, rng=np.random.default_rng(1))

    assert isinstance(result, TrainTestFitResult)
    assert result.n_train + result.n_test == data.shape[0]
    assert result.n_test == round(0.3 * data.shape[0])
    assert isinstance(result.in_sample, FitIndicesResult)
    assert isinstance(result.out_of_sample, FitIndicesResult)


def test_adjacency_matches_fit_on_the_training_rows_only() -> None:
    data = _chain_data(0)
    rng = np.random.default_rng(2)
    result = train_test_fit_indices(data, _fit(), test_proportion=0.5, rng=rng)

    rng_replay = np.random.default_rng(2)
    n_test = round(0.5 * data.shape[0])
    permutation = rng_replay.permutation(data.shape[0])
    train_rows = data[permutation[n_test:]]
    expected = fit_gopc(train_rows, screening_alpha=0.05, dpi_alpha=0.05)

    assert np.array_equal(result.adjacency, expected.adjacency)


def test_default_test_proportion_is_half() -> None:
    data = _chain_data(0)
    result = train_test_fit_indices(data, _fit(), rng=np.random.default_rng(0))
    assert result.n_test == round(0.5 * data.shape[0])
    assert result.n_train == data.shape[0] - result.n_test


def test_rejects_test_proportion_outside_open_unit_interval() -> None:
    data = _chain_data(0)
    with pytest.raises(ValueError, match="test_proportion"):
        train_test_fit_indices(data, _fit(), test_proportion=0.0, rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="test_proportion"):
        train_test_fit_indices(data, _fit(), test_proportion=1.0, rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="test_proportion"):
        train_test_fit_indices(data, _fit(), test_proportion=1.5, rng=np.random.default_rng(0))


def test_rejects_split_that_leaves_no_rows_on_one_side() -> None:
    data = _chain_data(0, n=4)
    with pytest.raises(ValueError, match="test_proportion leaves no rows"):
        train_test_fit_indices(data, _fit(), test_proportion=0.001, rng=np.random.default_rng(0))


def test_train_and_test_splits_are_disjoint_and_exhaustive() -> None:
    data = _chain_data(3)
    rng = np.random.default_rng(4)
    n_test = round(0.4 * data.shape[0])
    permutation = np.random.default_rng(4).permutation(data.shape[0])
    test_idx = set(permutation[:n_test].tolist())
    train_idx = set(permutation[n_test:].tolist())

    assert test_idx.isdisjoint(train_idx)
    assert test_idx | train_idx == set(range(data.shape[0]))

    result = train_test_fit_indices(data, _fit(), test_proportion=0.4, rng=rng)
    assert result.n_test == n_test


def test_out_of_sample_uses_the_held_out_rows_covariance() -> None:
    """A quick sanity check that in_sample/out_of_sample aren't
    accidentally evaluated on the same data: their sample covariances
    (recoverable via each FitIndicesResult's null model, whose fitted
    covariance is just the diagonal of the sample variances) should
    generally differ since they come from disjoint row sets."""
    data = _chain_data(5)
    result = train_test_fit_indices(data, _fit(), test_proportion=0.5, rng=np.random.default_rng(6))

    in_sample_diag = np.diag(result.in_sample.null.covariance)
    out_of_sample_diag = np.diag(result.out_of_sample.null.covariance)
    assert not np.allclose(in_sample_diag, out_of_sample_diag)
