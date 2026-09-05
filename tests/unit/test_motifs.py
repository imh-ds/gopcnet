import numpy as np
import pytest

from mintnet.simulation.motifs import (
    sample_chain,
    sample_measured_fork,
    sample_precision_triangle,
    triangle_precisions,
)


def test_chain_endpoint_correlation_is_weaker_than_adjacent_links():
    data = sample_chain(100_000, 0.7, np.random.default_rng(1))
    corr = np.corrcoef(data.T)
    assert corr[0, 2] < corr[0, 1]
    assert corr[0, 2] < corr[1, 2]


def test_measured_fork_endpoint_correlation_is_weaker_than_adjacent_links():
    data = sample_measured_fork(100_000, 0.7, np.random.default_rng(1))
    corr = np.corrcoef(data.T)
    assert corr[0, 2] < corr[0, 1]
    assert corr[0, 2] < corr[1, 2]


def test_triangle_precisions_are_positive_definite():
    for precision in triangle_precisions().values():
        np.linalg.cholesky(precision)
        assert np.all(np.abs(precision[np.triu_indices(3, 1)]) > 0)


def test_triangle_samples_are_standardized_and_seeded():
    first = sample_precision_triangle("balanced", 100, np.random.default_rng(42))
    second = sample_precision_triangle("balanced", 100, np.random.default_rng(42))
    assert np.array_equal(first, second)
    assert first.shape == (100, 3)
    assert np.allclose(first.mean(axis=0), 0.0)
    assert np.allclose(first.std(axis=0, ddof=1), 1.0)


@pytest.mark.parametrize("n", [0, -1])
def test_motifs_reject_nonpositive_sample_size(n):
    with pytest.raises(ValueError, match="n must be at least 1"):
        sample_chain(n, 0.7, np.random.default_rng(1))


def test_motifs_reject_invalid_strength():
    with pytest.raises(ValueError, match="0 < strength < 1"):
        sample_measured_fork(10, 1.0, np.random.default_rng(1))


def test_triangle_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown triangle"):
        sample_precision_triangle("unknown", 10, np.random.default_rng(1))
