"""Screen-then-prune pipeline composition, per docs/stage2b_charter.md.

Screening produces a candidate-edge graph. Candidate edges are grouped
into connected components; DPI conditioning is applied only within
components that are exactly a 3-node, 3-edge "candidate triad" -- the one
shape where "which variable to condition on" is unambiguous. Every other
component shape (isolated single edges, or anything larger/differently
shaped) is passed through unmodified. This is a scope boundary stated in
the charter, not an oversight.
"""

from itertools import combinations

import numpy as np
from scipy.sparse.csgraph import connected_components as _scipy_connected_components

from mintnet.dpi import prune_conditional_independence


def connected_components(flagged: np.ndarray) -> list[frozenset[int]]:
    """Group nodes with at least one candidate edge into connected components."""
    p = flagged.shape[0]
    _, labels = _scipy_connected_components(csgraph=flagged, directed=False)
    groups: dict[int, set[int]] = {}
    for node, label in enumerate(labels):
        groups.setdefault(int(label), set()).add(node)
    return [frozenset(nodes) for nodes in groups.values() if len(nodes) >= 2]


def _is_candidate_triad(component: frozenset[int], flagged: np.ndarray) -> bool:
    if len(component) != 3:
        return False
    nodes = sorted(component)
    return all(flagged[i, j] for i, j in combinations(nodes, 2))


def compose_screen_then_prune(
    data: np.ndarray, flagged: np.ndarray, alpha: float
) -> tuple[np.ndarray, dict[frozenset[int], bool]]:
    """Apply DPI within every candidate triad; pass through every other component.

    Returns the final p x p adjacency matrix and a dict mapping each
    connected component to whether it was a candidate triad (for
    descriptive reporting of how often DPI actually had a chance to act).
    """
    p = flagged.shape[0]
    final = flagged.copy()
    triad_flags: dict[frozenset[int], bool] = {}

    for component in connected_components(flagged):
        is_triad = _is_candidate_triad(component, flagged)
        triad_flags[component] = is_triad
        if not is_triad:
            continue
        nodes = sorted(component)
        sub_data = data[:, nodes]
        sub_adjacency = prune_conditional_independence(sub_data, alpha)
        for local_i, local_j in combinations(range(3), 2):
            final[nodes[local_i], nodes[local_j]] = sub_adjacency[local_i, local_j]
            final[nodes[local_j], nodes[local_i]] = sub_adjacency[local_i, local_j]

    return final, triad_flags
