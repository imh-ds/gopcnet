import numpy as np
import pytest

from mintnet.pipeline import compose_screen_then_prune, connected_components
from mintnet.simulation import sample_chain, sample_hub


def test_connected_components_groups_a_triangle_and_an_isolated_edge():
    flagged = np.zeros((6, 6), dtype=bool)
    for i, j in ((0, 1), (0, 2), (1, 2), (3, 4)):
        flagged[i, j] = flagged[j, i] = True
    # nodes 5 has no candidate edges at all.

    components = connected_components(flagged)

    assert frozenset({0, 1, 2}) in components
    assert frozenset({3, 4}) in components
    assert len(components) == 2
    assert not any(5 in c for c in components)


def test_compose_prunes_the_indirect_edge_within_a_candidate_triad():
    rng = np.random.default_rng(1)
    data = sample_chain(2000, 0.7, rng)  # columns 0,1,2 = X1,X2,X3
    flagged = np.zeros((3, 3), dtype=bool)
    for i, j in ((0, 1), (0, 2), (1, 2)):  # a full candidate triad, incl. the indirect pair
        flagged[i, j] = flagged[j, i] = True

    final, shapes = compose_screen_then_prune(data, flagged, alpha=0.15)

    shape = shapes[frozenset({0, 1, 2})]
    assert shape["size"] == 3 and shape["is_clique"] and shape["is_validated_shape"]
    assert final[0, 1] and final[1, 2]  # direct edges retained
    assert not final[0, 2]  # indirect edge pruned


def test_compose_prunes_correctly_within_a_candidate_hub_clique():
    """The 4-node hub shape is also a validated clique size (D-015)."""
    rng = np.random.default_rng(4)
    data = sample_hub(2000, 0.7, children=3, rng=rng)  # hub=0, children=1,2,3
    flagged = np.zeros((4, 4), dtype=bool)
    from itertools import combinations

    for i, j in combinations(range(4), 2):  # a full 4-clique candidate component
        flagged[i, j] = flagged[j, i] = True

    final, shapes = compose_screen_then_prune(data, flagged, alpha=0.15)

    shape = shapes[frozenset({0, 1, 2, 3})]
    assert shape["size"] == 4 and shape["is_clique"] and shape["is_validated_shape"]
    assert final[0, 1] and final[0, 2] and final[0, 3]  # hub-child edges retained
    assert not final[1, 2] and not final[1, 3] and not final[2, 3]  # child-child pruned


def test_compose_passes_through_an_isolated_two_node_component_unmodified():
    """DPI cannot condition a lone edge on anything -- it must pass through as-is."""
    rng = np.random.default_rng(2)
    data = rng.normal(size=(500, 4))
    flagged = np.zeros((4, 4), dtype=bool)
    flagged[0, 1] = flagged[1, 0] = True  # a single isolated candidate edge

    final, shapes = compose_screen_then_prune(data, flagged, alpha=0.15)

    shape = shapes[frozenset({0, 1})]
    assert shape["size"] == 2 and not shape["is_validated_shape"]
    assert np.array_equal(final, flagged)


def test_compose_does_not_treat_a_3_node_path_as_a_candidate_clique():
    """3 nodes but only 2 candidate edges (a path) is not a clique."""
    rng = np.random.default_rng(3)
    data = rng.normal(size=(500, 3))
    flagged = np.zeros((3, 3), dtype=bool)
    flagged[0, 1] = flagged[1, 0] = True
    flagged[1, 2] = flagged[2, 1] = True
    # (0, 2) is not a candidate edge -- only 2 edges among 3 nodes.

    final, shapes = compose_screen_then_prune(data, flagged, alpha=0.15)

    shape = shapes[frozenset({0, 1, 2})]
    assert not shape["is_clique"] and not shape["is_validated_shape"]
    assert np.array_equal(final, flagged)  # passed through unmodified


def test_compose_passes_through_a_5_node_clique_as_an_unvalidated_shape():
    """A clique of size 5 is mechanically a clique but not a validated size."""
    rng = np.random.default_rng(5)
    data = rng.normal(size=(500, 5))
    flagged = np.ones((5, 5), dtype=bool)
    np.fill_diagonal(flagged, False)

    final, shapes = compose_screen_then_prune(data, flagged, alpha=0.15)

    shape = shapes[frozenset({0, 1, 2, 3, 4})]
    assert shape["size"] == 5 and shape["is_clique"] and not shape["is_validated_shape"]
    assert np.array_equal(final, flagged)  # passed through unmodified, not pruned
