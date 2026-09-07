from functools import partial

import numpy as np
import pytest

from gopcnet import bootstrap_edge_stability, fit_gopc
from gopcnet.stability import threshold_by_inclusion_probability


def test_thresholds_edges_at_or_above_the_cutoff() -> None:
    inclusion = np.array([[0.0, 0.9, 0.3], [0.9, 0.0, 0.5], [0.3, 0.5, 0.0]])
    adjacency = threshold_by_inclusion_probability(inclusion, threshold=0.5)
    expected = np.array([[False, True, False], [True, False, True], [False, True, False]])
    assert np.array_equal(adjacency, expected)


def test_diagonal_is_always_false_even_if_input_diagonal_is_nonzero() -> None:
    inclusion = np.array([[1.0, 0.9], [0.9, 1.0]])
    adjacency = threshold_by_inclusion_probability(inclusion, threshold=0.5)
    assert not adjacency[0, 0]
    assert not adjacency[1, 1]


def test_default_threshold_is_one_half() -> None:
    inclusion = np.array([[0.0, 0.5], [0.5, 0.0]])
    adjacency = threshold_by_inclusion_probability(inclusion)
    assert adjacency[0, 1] and adjacency[1, 0]


def test_rejects_threshold_outside_unit_interval() -> None:
    inclusion = np.array([[0.0, 0.5], [0.5, 0.0]])
    with pytest.raises(ValueError):
        threshold_by_inclusion_probability(inclusion, threshold=-0.1)
    with pytest.raises(ValueError):
        threshold_by_inclusion_probability(inclusion, threshold=1.1)


def test_rejects_non_square_matrix() -> None:
    with pytest.raises(ValueError):
        threshold_by_inclusion_probability(np.zeros((2, 3)))


def test_end_to_end_with_bootstrap_edge_stability() -> None:
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=400)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.36) * rng.normal(size=400)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.36) * rng.normal(size=400)
    data = np.column_stack([x1, x2, x3])

    fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)
    stability = bootstrap_edge_stability(data, fit, bootstraps=30, rng=np.random.default_rng(1))
    adjacency = threshold_by_inclusion_probability(stability.inclusion_probability, threshold=0.9)

    assert adjacency.shape == (3, 3)
    assert adjacency.dtype == bool
    assert np.array_equal(adjacency, adjacency.T)
