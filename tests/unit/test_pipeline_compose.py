import numpy as np
import pytest

from mintnet.pipeline import compose_screen_then_prune, connected_components
from mintnet.simulation import sample_chain


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

    final, triad_flags = compose_screen_then_prune(data, flagged, alpha=0.15)

    assert triad_flags[frozenset({0, 1, 2})] is True
    assert final[0, 1] and final[1, 2]  # direct edges retained
    assert not final[0, 2]  # indirect edge pruned


def test_compose_passes_through_an_isolated_two_node_component_unmodified():
    """DPI cannot condition a lone edge on anything -- it must pass through as-is."""
    rng = np.random.default_rng(2)
    data = rng.normal(size=(500, 4))
    flagged = np.zeros((4, 4), dtype=bool)
    flagged[0, 1] = flagged[1, 0] = True  # a single isolated candidate edge

    final, triad_flags = compose_screen_then_prune(data, flagged, alpha=0.15)

    assert triad_flags[frozenset({0, 1})] is False
    assert final[0, 1] is np.bool_(True) or final[0, 1] == True  # noqa: E712
    assert np.array_equal(final, flagged)


def test_compose_does_not_treat_a_3_node_path_as_a_candidate_triad():
    """3 nodes but only 2 candidate edges (a path) is not the triad shape."""
    rng = np.random.default_rng(3)
    data = rng.normal(size=(500, 3))
    flagged = np.zeros((3, 3), dtype=bool)
    flagged[0, 1] = flagged[1, 0] = True
    flagged[1, 2] = flagged[2, 1] = True
    # (0, 2) is not a candidate edge -- only 2 edges among 3 nodes.

    final, triad_flags = compose_screen_then_prune(data, flagged, alpha=0.15)

    assert triad_flags[frozenset({0, 1, 2})] is False
    assert np.array_equal(final, flagged)  # passed through unmodified
