import numpy as np

from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence
from gopcnet.pipeline.weights import compute_fixed_order_weights, compute_growing_order_weights
from gopcnet.screening import compute_pairwise_screening_evidence


def _chain_data(seed: int, n: int = 500) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_untested_edge_falls_back_to_marginal_correlation() -> None:
    """An edge whose component was never DPI-tested (not a validated
    clique shape) keeps the raw screening correlation as its weight."""
    data = _chain_data(0)
    adjacency = np.array([[False, True, False], [True, False, False], [False, False, False]])
    shapes = {frozenset({0, 1}): {"size": 2, "is_clique": True, "is_validated_shape": False}}

    weights = compute_fixed_order_weights(data, adjacency, shapes)

    marginal = compute_pairwise_screening_evidence(data).correlation
    assert np.isclose(weights[0, 1], marginal[0, 1])
    assert weights[0, 2] == 0.0
    assert weights[1, 2] == 0.0


def test_fixed_order_weight_is_the_single_conditioning_test() -> None:
    data = _chain_data(0)
    adjacency = np.array([[False, True, False], [True, False, True], [False, True, False]])
    shapes = {frozenset({0, 1, 2}): {"size": 3, "is_clique": True, "is_validated_shape": True}}

    weights = compute_fixed_order_weights(data, adjacency, shapes)

    expected_01 = compute_partial_correlation_evidence(data, 0, 1, [2]).partial_correlation
    expected_12 = compute_partial_correlation_evidence(data, 1, 2, [0]).partial_correlation
    assert np.isclose(weights[0, 1], expected_01)
    assert np.isclose(weights[1, 2], expected_12)
    assert weights[0, 2] == 0.0  # never a candidate edge -- not in adjacency


def test_weights_are_zero_wherever_adjacency_is_false() -> None:
    data = _chain_data(0)
    adjacency = np.zeros((3, 3), dtype=bool)
    shapes = {frozenset({0, 1, 2}): {"size": 3, "is_clique": True, "is_validated_shape": True}}

    weights = compute_fixed_order_weights(data, adjacency, shapes)

    assert np.all(weights == 0.0)


def test_growing_order_weight_is_the_weakest_tested_subset() -> None:
    """Retention under growing-order DPI requires every tested subset,
    across every size up to the deciding one, to reject independence --
    so the weight convention (min |partial correlation| among them) is
    reproducible by directly re-running the same subsets."""
    data = _chain_data(3, n=400)
    p = data.shape[1]
    adjacency = np.array([[False, True, True], [True, False, True], [True, True, False]])
    flagged = adjacency.copy()
    conditioning_size_used = {(0, 1): 1, (0, 2): 1, (1, 2): 1}

    weights = compute_growing_order_weights(
        data, adjacency, flagged, conditioning_size_used, max_conditioning_size=4
    )

    for i, j in ((0, 1), (0, 2), (1, 2)):
        (other,) = [k for k in range(p) if k not in (i, j)]
        expected = compute_partial_correlation_evidence(data, i, j, [other]).partial_correlation
        assert np.isclose(weights[i, j], expected)


def test_growing_order_untested_edge_falls_back_to_marginal_correlation() -> None:
    data = _chain_data(0)
    adjacency = np.array([[False, True, False], [True, False, False], [False, False, False]])
    flagged = adjacency.copy()
    conditioning_size_used = {(0, 1): 0}

    weights = compute_growing_order_weights(
        data, adjacency, flagged, conditioning_size_used, max_conditioning_size=4
    )

    marginal = compute_pairwise_screening_evidence(data).correlation
    assert np.isclose(weights[0, 1], marginal[0, 1])


def test_weights_matrix_is_symmetric_with_zero_diagonal() -> None:
    data = _chain_data(0)
    adjacency = np.array([[False, True, False], [True, False, True], [False, True, False]])
    shapes = {frozenset({0, 1, 2}): {"size": 3, "is_clique": True, "is_validated_shape": True}}

    weights = compute_fixed_order_weights(data, adjacency, shapes)

    assert np.array_equal(weights, weights.T)
    assert np.all(np.diag(weights) == 0.0)
