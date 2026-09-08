import numpy as np
import pytest

from gopcnet.metrics.bridge_centrality import (
    BridgeCentralityResult,
    bridge_betweenness_centrality,
    bridge_closeness_centrality,
    bridge_expected_influence,
    bridge_strength,
    compute_bridge_centrality,
)
from gopcnet.metrics.centrality import (
    betweenness_centrality,
    closeness_centrality,
    expected_influence,
    strength,
)


def _path_graph_4() -> np.ndarray:
    """0 -- 1 -- 2 -- 3, every edge weight exactly 1.0."""
    w = np.zeros((4, 4))
    for i, j in ((0, 1), (1, 2), (2, 3)):
        w[i, j] = w[j, i] = 1.0
    return w


def _cycle_graph_4() -> np.ndarray:
    w = np.zeros((4, 4))
    for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
        w[i, j] = w[j, i] = 1.0
    return w


# --- singleton communities: bridge measures must equal ordinary centrality exactly ---


def test_singleton_communities_make_bridge_strength_match_ordinary_strength() -> None:
    w = _path_graph_4()
    communities = np.arange(4)  # every node its own community
    assert np.allclose(bridge_strength(w, communities), strength(w))


def test_singleton_communities_make_bridge_expected_influence_match_ordinary() -> None:
    w = np.array([[0.0, 0.5, -0.5], [0.5, 0.0, 0.0], [-0.5, 0.0, 0.0]])
    communities = np.arange(3)
    assert np.allclose(bridge_expected_influence(w, communities), expected_influence(w))


def test_singleton_communities_make_bridge_closeness_match_ordinary() -> None:
    w = _path_graph_4()
    communities = np.arange(4)
    assert np.allclose(bridge_closeness_centrality(w, communities), closeness_centrality(w))


def test_singleton_communities_make_bridge_betweenness_match_ordinary() -> None:
    w = _cycle_graph_4()
    communities = np.arange(4)
    assert np.allclose(bridge_betweenness_centrality(w, communities), betweenness_centrality(w))


# --- one shared community: every bridge measure must be exactly zero ---


def test_single_shared_community_gives_zero_bridge_strength() -> None:
    w = _path_graph_4()
    communities = np.zeros(4, dtype=int)
    assert np.allclose(bridge_strength(w, communities), 0.0)


def test_single_shared_community_gives_zero_bridge_expected_influence() -> None:
    w = np.array([[0.0, 0.5, -0.5], [0.5, 0.0, 0.0], [-0.5, 0.0, 0.0]])
    communities = np.zeros(3, dtype=int)
    assert np.allclose(bridge_expected_influence(w, communities), 0.0)


def test_single_shared_community_gives_zero_bridge_closeness() -> None:
    w = _path_graph_4()
    communities = np.zeros(4, dtype=int)
    assert np.allclose(bridge_closeness_centrality(w, communities), 0.0)


def test_single_shared_community_gives_zero_bridge_betweenness() -> None:
    w = _cycle_graph_4()
    communities = np.zeros(4, dtype=int)
    assert np.allclose(bridge_betweenness_centrality(w, communities), 0.0)


# --- hand-computed two-community example ---


def test_bridge_strength_on_two_triangles_sharing_a_bridge_node() -> None:
    # {0,1,2} in community A, {3,4} in community B; node 2 connects to node 3
    # (the only cross-community edge) in addition to its within-community edges.
    p = 5
    w = np.zeros((p, p))
    for i, j in ((0, 1), (0, 2), (1, 2)):
        w[i, j] = w[j, i] = 1.0
    w[2, 3] = w[3, 2] = 0.5  # the single bridge edge
    w[3, 4] = w[4, 3] = 1.0
    communities = np.array(["A", "A", "A", "B", "B"])

    bridge = bridge_strength(w, communities)
    # node 2's only cross-community edge is to node 3 (weight 0.5)
    assert bridge[2] == pytest.approx(0.5)
    # nodes 0, 1 have no cross-community edges at all
    assert bridge[0] == pytest.approx(0.0)
    assert bridge[1] == pytest.approx(0.0)
    # node 3's cross-community edge is to node 2 (weight 0.5); its edge to 4 is within-community
    assert bridge[3] == pytest.approx(0.5)
    assert bridge[4] == pytest.approx(0.0)


def test_bridge_betweenness_on_two_triangles_sharing_a_bridge_node() -> None:
    # A triangle {0,1,2} (community A) with a path tail 2-3-4 (node 3, 4 in
    # community B). All 6 cross-community pairs and their unique shortest
    # paths: (0,3) via 2 [len 2]; (0,4) via 2,3 [len 3]; (1,3) via 2 [len 2];
    # (1,4) via 2,3 [len 3]; (2,3) direct [len 1]; (2,4) via 3 [len 2].
    # Node 2 is an internal (non-endpoint) node on (0,3),(0,4),(1,3),(1,4) ->
    # 4 pairs. Node 3 is internal on (0,4),(1,4),(2,4) -> 3 pairs. Nodes
    # 0, 1, 4 are never internal on any cross-community pair's shortest
    # path. Sanity check: sum of (path length - 1) over all 6 pairs is
    # 1+2+1+2+0+1 = 7, matching 4 + 3 = 7.
    p = 5
    w = np.zeros((p, p))
    for i, j in ((0, 1), (0, 2), (1, 2)):
        w[i, j] = w[j, i] = 1.0
    w[2, 3] = w[3, 2] = 1.0
    w[3, 4] = w[4, 3] = 1.0
    communities = np.array(["A", "A", "A", "B", "B"])

    bridge_betweenness = bridge_betweenness_centrality(w, communities)
    assert bridge_betweenness[0] == pytest.approx(0.0)
    assert bridge_betweenness[1] == pytest.approx(0.0)
    assert bridge_betweenness[2] == pytest.approx(4.0)
    assert bridge_betweenness[3] == pytest.approx(3.0)
    assert bridge_betweenness[4] == pytest.approx(0.0)


# --- validation ---


def test_rejects_communities_with_wrong_length() -> None:
    w = _path_graph_4()
    with pytest.raises(ValueError, match="one entry per node"):
        bridge_strength(w, np.array([0, 0, 1]))


def test_rejects_communities_with_wrong_shape() -> None:
    w = _path_graph_4()
    with pytest.raises(ValueError, match="one-dimensional"):
        bridge_strength(w, np.zeros((4, 1)))


def test_compute_bridge_centrality_bundles_all_four() -> None:
    w = _path_graph_4()
    communities = np.array([0, 0, 1, 1])
    result = compute_bridge_centrality(w, communities)

    assert isinstance(result, BridgeCentralityResult)
    assert np.allclose(result.strength, bridge_strength(w, communities))
    assert np.allclose(result.expected_influence, bridge_expected_influence(w, communities))
    assert np.allclose(result.closeness, bridge_closeness_centrality(w, communities))
    assert np.allclose(result.betweenness, bridge_betweenness_centrality(w, communities))
