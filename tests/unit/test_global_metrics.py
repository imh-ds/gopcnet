import math

import numpy as np
import pytest

from gopcnet.metrics.global_metrics import (
    GlobalMetricsResult,
    average_shortest_path_length,
    compute_global_metrics,
    density,
    global_clustering_coefficient,
    global_strength,
)


def _triangle_adjacency() -> np.ndarray:
    # 3 nodes, all mutually connected -- one closed triangle.
    adjacency = np.array(
        [
            [False, True, True],
            [True, False, True],
            [True, True, False],
        ]
    )
    return adjacency


def _path_adjacency() -> np.ndarray:
    # 3 nodes in a chain: 0-1-2, no 0-2 edge -- one open triple, no triangle.
    adjacency = np.array(
        [
            [False, True, False],
            [True, False, True],
            [False, True, False],
        ]
    )
    return adjacency


def _weights_from_adjacency(adjacency: np.ndarray, weight: float = 0.5) -> np.ndarray:
    return np.where(adjacency, weight, 0.0)


# --- density ---------------------------------------------------------------


def test_density_of_a_triangle_is_one() -> None:
    assert density(_triangle_adjacency()) == pytest.approx(1.0)


def test_density_of_a_path_is_two_thirds() -> None:
    assert density(_path_adjacency()) == pytest.approx(2.0 / 3.0)


def test_density_of_an_empty_network_is_zero() -> None:
    adjacency = np.zeros((4, 4), dtype=bool)
    assert density(adjacency) == pytest.approx(0.0)


def test_density_of_a_single_node_is_nan() -> None:
    adjacency = np.zeros((1, 1), dtype=bool)
    assert math.isnan(density(adjacency))


def test_density_rejects_non_square_input() -> None:
    with pytest.raises(ValueError, match="square"):
        density(np.zeros((3, 4), dtype=bool))


def test_density_rejects_asymmetric_input() -> None:
    adjacency = np.array([[False, True], [False, False]])
    with pytest.raises(ValueError, match="symmetric"):
        density(adjacency)


def test_density_rejects_nonzero_diagonal() -> None:
    adjacency = np.array([[True, False], [False, False]])
    with pytest.raises(ValueError, match="diagonal"):
        density(adjacency)


# --- global_strength ---------------------------------------------------------


def test_global_strength_of_a_triangle() -> None:
    weights = _weights_from_adjacency(_triangle_adjacency(), weight=0.5)
    assert global_strength(weights) == pytest.approx(1.5)  # 3 edges * 0.5


def test_global_strength_uses_absolute_value() -> None:
    weights = np.array(
        [
            [0.0, -0.5, 0.0],
            [-0.5, 0.0, 0.5],
            [0.0, 0.5, 0.0],
        ]
    )
    assert global_strength(weights) == pytest.approx(1.0)  # |-0.5| + |0.5|


def test_global_strength_of_an_empty_network_is_zero() -> None:
    weights = np.zeros((3, 3))
    assert global_strength(weights) == pytest.approx(0.0)


# --- global_clustering_coefficient -------------------------------------------


def test_clustering_coefficient_of_a_triangle_is_one() -> None:
    assert global_clustering_coefficient(_triangle_adjacency()) == pytest.approx(1.0)


def test_clustering_coefficient_of_an_open_path_is_zero() -> None:
    assert global_clustering_coefficient(_path_adjacency()) == pytest.approx(0.0)


def test_clustering_coefficient_of_two_triangles_sharing_a_node() -> None:
    # {0,1,2} and {2,3,4} each fully connected, sharing node 2.
    p = 5
    adjacency = np.zeros((p, p), dtype=bool)
    for i, j in [(0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4)]:
        adjacency[i, j] = True
        adjacency[j, i] = True

    # Manual count: 2 closed triangles. Connected triples = sum_v C(deg(v), 2):
    # deg = [2, 2, 4, 2, 2] -> C(2,2)=1 (x4) + C(4,2)=6 -> 4 + 6 = 10.
    # transitivity = 3 * 2 / 10 = 0.6
    assert global_clustering_coefficient(adjacency) == pytest.approx(0.6)


def test_clustering_coefficient_is_nan_with_no_connected_triples() -> None:
    adjacency = np.zeros((3, 3), dtype=bool)
    adjacency[0, 1] = adjacency[1, 0] = True  # a single edge: no triples possible
    assert math.isnan(global_clustering_coefficient(adjacency))


# --- average_shortest_path_length --------------------------------------------


def test_average_shortest_path_length_of_a_triangle_with_unit_weights() -> None:
    weights = _weights_from_adjacency(_triangle_adjacency(), weight=1.0)
    # every pair directly connected at distance 1/1 = 1
    assert average_shortest_path_length(weights) == pytest.approx(1.0)


def test_average_shortest_path_length_of_a_path_sums_hops() -> None:
    weights = _weights_from_adjacency(_path_adjacency(), weight=1.0)
    # distances: (0,1)=1, (1,2)=1, (0,2)=1+1=2 -> mean = 4/3
    assert average_shortest_path_length(weights) == pytest.approx(4.0 / 3.0)


def test_average_shortest_path_length_excludes_unreachable_pairs() -> None:
    # nodes {0,1} connected, node 2 isolated.
    weights = np.zeros((3, 3))
    weights[0, 1] = weights[1, 0] = 1.0
    assert average_shortest_path_length(weights) == pytest.approx(1.0)


def test_average_shortest_path_length_is_nan_with_no_reachable_pairs() -> None:
    weights = np.zeros((3, 3))
    assert math.isnan(average_shortest_path_length(weights))


def test_average_shortest_path_length_uses_inverse_magnitude_distance() -> None:
    weights = np.zeros((2, 2))
    weights[0, 1] = weights[1, 0] = -0.25  # sign shouldn't matter for distance
    assert average_shortest_path_length(weights) == pytest.approx(4.0)


# --- compute_global_metrics ---------------------------------------------------


def test_compute_global_metrics_bundles_all_four() -> None:
    adjacency = _triangle_adjacency()
    weights = _weights_from_adjacency(adjacency, weight=0.5)
    result = compute_global_metrics(adjacency, weights)

    assert isinstance(result, GlobalMetricsResult)
    assert result.density == pytest.approx(density(adjacency))
    assert result.global_strength == pytest.approx(global_strength(weights))
    assert result.clustering_coefficient == pytest.approx(global_clustering_coefficient(adjacency))
    assert result.average_shortest_path_length == pytest.approx(average_shortest_path_length(weights))


def test_compute_global_metrics_rejects_mismatched_shapes() -> None:
    adjacency = np.zeros((3, 3), dtype=bool)
    weights = np.zeros((4, 4))
    with pytest.raises(ValueError, match="same shape"):
        compute_global_metrics(adjacency, weights)
