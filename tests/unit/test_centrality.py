import numpy as np
import pytest

from gopcnet.metrics.centrality import (
    CentralityResult,
    betweenness_centrality,
    closeness_centrality,
    compute_centrality,
    expected_influence,
    strength,
)


def _path_graph_4() -> np.ndarray:
    """0 -- 1 -- 2 -- 3, every edge weight exactly 1.0."""
    w = np.zeros((4, 4))
    for i, j in ((0, 1), (1, 2), (2, 3)):
        w[i, j] = w[j, i] = 1.0
    return w


def test_strength_matches_hand_computation_on_a_path_graph() -> None:
    w = _path_graph_4()
    assert np.allclose(strength(w), [1.0, 2.0, 2.0, 1.0])


def test_expected_influence_matches_strength_when_all_weights_positive() -> None:
    w = _path_graph_4()
    assert np.allclose(expected_influence(w), strength(w))


def test_expected_influence_diverges_from_strength_with_a_negative_edge() -> None:
    w = np.array([[0.0, 0.5, -0.5], [0.5, 0.0, 0.0], [-0.5, 0.0, 0.0]])
    assert np.allclose(strength(w), [1.0, 0.5, 0.5])
    assert np.allclose(expected_influence(w), [0.0, 0.5, -0.5])


def test_closeness_matches_hand_computation_on_a_path_graph() -> None:
    w = _path_graph_4()
    # node0: dist to 1,2,3 = 1,2,3 -> sum 6 -> 1/6
    # node1: dist to 0,2,3 = 1,1,2 -> sum 4 -> 1/4
    expected = np.array([1 / 6, 1 / 4, 1 / 4, 1 / 6])
    assert np.allclose(closeness_centrality(w), expected)


def test_betweenness_matches_hand_computation_on_a_path_graph() -> None:
    """Unordered pairs whose unique shortest path crosses each node:
    node1 lies on (0,2) and (0,3); node2 lies on (1,3) and (0,3);
    node0 and node3 are never an intermediate node."""
    w = _path_graph_4()
    assert np.allclose(betweenness_centrality(w), [0.0, 2.0, 2.0, 0.0])


def test_betweenness_splits_ties_proportionally_not_arbitrarily() -> None:
    """A 4-cycle (0-1-2-3-0), equal weights: both length-2 paths from 0
    to 2 (via 1, via 3) are equally short, so each contributes half."""
    w = np.zeros((4, 4))
    for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
        w[i, j] = w[j, i] = 1.0

    betweenness = betweenness_centrality(w)
    # Every node sits on exactly one "diagonal" pair's two tied shortest
    # paths, contributing 0.5 from each of the two diagonal pairs.
    assert np.allclose(betweenness, [0.5, 0.5, 0.5, 0.5])


def test_closeness_and_betweenness_use_absolute_weight_for_distance() -> None:
    """Sign must not change path length -- a -1.0 edge and a +1.0 edge
    are equally short connections (qgraph/bootnet convention)."""
    w_positive = np.array([[0.0, 1.0], [1.0, 0.0]])
    w_negative = np.array([[0.0, -1.0], [-1.0, 0.0]])
    assert np.allclose(closeness_centrality(w_positive), closeness_centrality(w_negative))
    assert np.allclose(betweenness_centrality(w_positive), betweenness_centrality(w_negative))


def test_isolated_node_gets_zero_closeness_and_zero_betweenness() -> None:
    w = np.zeros((3, 3))
    w[0, 1] = w[1, 0] = 1.0  # node 2 is isolated

    closeness = closeness_centrality(w)
    betweenness = betweenness_centrality(w)
    assert closeness[2] == 0.0
    assert betweenness[2] == 0.0


def test_stronger_weight_means_shorter_distance_so_higher_closeness() -> None:
    weak = np.array([[0.0, 0.1, 0.0], [0.1, 0.0, 0.1], [0.0, 0.1, 0.0]])
    strong = np.array([[0.0, 0.9, 0.0], [0.9, 0.0, 0.9], [0.0, 0.9, 0.0]])
    assert closeness_centrality(strong)[0] > closeness_centrality(weak)[0]


def test_compute_centrality_bundles_all_four_measures() -> None:
    w = _path_graph_4()
    result = compute_centrality(w)
    assert isinstance(result, CentralityResult)
    assert np.allclose(result.strength, strength(w))
    assert np.allclose(result.expected_influence, expected_influence(w))
    assert np.allclose(result.closeness, closeness_centrality(w))
    assert np.allclose(result.betweenness, betweenness_centrality(w))


def test_rejects_non_square_matrix() -> None:
    with pytest.raises(ValueError):
        strength(np.zeros((3, 4)))


def test_rejects_asymmetric_matrix() -> None:
    w = np.array([[0.0, 1.0], [0.0, 0.0]])
    with pytest.raises(ValueError):
        strength(w)


def test_rejects_nonzero_diagonal() -> None:
    w = np.array([[1.0, 0.5], [0.5, 0.0]])
    with pytest.raises(ValueError):
        strength(w)
