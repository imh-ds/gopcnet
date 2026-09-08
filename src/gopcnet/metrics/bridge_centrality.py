"""Bridge centrality (Jones, Ma, & McNally, 2021) -- how much a node
connects *across* community boundaries, as distinct from
`gopcnet.metrics.centrality`'s plain node centrality, which counts
every edge equally regardless of which community either endpoint
belongs to.

Widely used in psychopathology network research (e.g. comorbidity
networks, where "communities" are diagnostic categories) to identify
which symptoms link two otherwise-separate clusters together, since a
node can have low overall strength/betweenness but still be the
critical link between two communities (or vice versa: a node highly
central *within* its own community but irrelevant to any other).

Every function here takes a `communities` array -- one label per node,
any hashable type (int cluster ids, diagnostic-category strings,
whatever the caller's own theory or clustering produced) -- as a
**caller-supplied** input, not something this module computes.
`gopcnet` has no community-detection algorithm of its own (no
`networkx`/`igraph` dependency, and community detection is a
different, disputed-methodology problem better left to a dedicated
tool or the caller's own theory) -- see `docs/decision_log.md`'s D-063
for that scope decision.

Four measures, each restricting one of `gopcnet.metrics.centrality`'s
own measures to cross-community relationships, and bundled by
`compute_bridge_centrality`:

- `bridge_strength`: sum of `|weight|` over edges to nodes in a
  *different* community only (same `1 / |weight|`-free, direct-weight
  convention `strength` uses).
- `bridge_expected_influence`: signed sum of weight to nodes in a
  different community only.
- `bridge_closeness_centrality`: the reciprocal of the sum of
  shortest-path distances (same `1 / |weight|` convention as
  `closeness_centrality`) from a node to every *other-community* node
  it can reach -- the path itself may pass through same-community
  nodes; only the target's community matters.
- `bridge_betweenness_centrality`: for every pair of nodes that
  themselves belong to *different* communities from each other
  (regardless of the bridge node's own community), the fraction of
  their shortest paths passing through this node, summed over all such
  pairs (full Brandes accumulation, restricted to cross-community
  target pairs -- see that function's own docstring for exactly how
  the restriction is implemented).

A strong, non-tunable sanity check used in this module's own tests:
if every node is placed in its own unique community, every bridge
measure reduces *exactly* to its ordinary `centrality` counterpart
(every neighbor is necessarily in a different community); if every
node shares one community, every bridge measure is exactly zero (no
cross-community relationship exists at all).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .centrality import _dijkstra_with_paths, _distance_matrix, _validate_weights


def _validate_communities(communities: np.ndarray, p: int) -> np.ndarray:
    values = np.asarray(communities)
    if values.ndim != 1 or values.shape[0] != p:
        raise ValueError("communities must be a one-dimensional array with one entry per node in weights")
    return values


def bridge_strength(weights: np.ndarray, communities: np.ndarray) -> np.ndarray:
    """Unsigned bridge strength: sum of `|weight|` over each node's
    edges to nodes in a *different* community only. Same-community
    edges contribute nothing, however strong."""
    values = _validate_weights(weights)
    community_labels = _validate_communities(communities, values.shape[0])
    cross_community = community_labels[:, None] != community_labels[None, :]
    return np.where(cross_community, np.abs(values), 0.0).sum(axis=1)


def bridge_expected_influence(weights: np.ndarray, communities: np.ndarray) -> np.ndarray:
    """Signed bridge expected influence: sum of weight (not `|weight|`)
    over each node's edges to nodes in a different community only."""
    values = _validate_weights(weights)
    community_labels = _validate_communities(communities, values.shape[0])
    cross_community = community_labels[:, None] != community_labels[None, :]
    return np.where(cross_community, values, 0.0).sum(axis=1)


def bridge_closeness_centrality(weights: np.ndarray, communities: np.ndarray) -> np.ndarray:
    """Bridge closeness: the reciprocal of the sum of shortest-path
    distances (`1 / |weight|` per edge, `closeness_centrality`'s own
    convention) from a node to every *other-community* node it can
    reach. The shortest path itself may pass through same-community
    nodes along the way -- only each target's community matters, not
    the route. `0.0` if no other-community node is reachable at all."""
    values = _validate_weights(weights)
    community_labels = _validate_communities(communities, values.shape[0])
    distance = _distance_matrix(values)
    p = distance.shape[0]
    closeness = np.zeros(p)
    for source in range(p):
        dist, _sigma, _predecessors, _order = _dijkstra_with_paths(distance, source)
        cross_community_reachable = np.isfinite(dist) & (community_labels != community_labels[source])
        total = dist[cross_community_reachable].sum()
        closeness[source] = 1.0 / total if total > 0 else 0.0
    return closeness


def bridge_betweenness_centrality(weights: np.ndarray, communities: np.ndarray) -> np.ndarray:
    """Bridge betweenness: for every pair of nodes `(s, t)` that belong
    to *different* communities from *each other* (independent of the
    bridge node's own community), the fraction of their shortest paths
    passing through this node, summed over all such pairs.

    Implemented as a one-line modification of `betweenness_centrality`'s
    own Brandes accumulation: normally, when node `w` is folded into its
    predecessor `v`'s dependency during the backward pass, `w` always
    contributes a base term of `1` (counting `w` itself as a valid
    target reached via `v`). Here that base term is `1` only when `w`
    and the current source `s` are in different communities, `0`
    otherwise -- so a same-community target contributes nothing as an
    *endpoint*, while still correctly propagating as an *intermediate*
    node for any further, cross-community target beyond it (`delta[w]`
    itself is untouched by the restriction). Ties are still split
    proportionally, exactly as in the unrestricted algorithm.
    """
    values = _validate_weights(weights)
    community_labels = _validate_communities(communities, values.shape[0])
    distance = _distance_matrix(values)
    p = distance.shape[0]
    betweenness = np.zeros(p)

    for source in range(p):
        _dist, sigma, predecessors, order = _dijkstra_with_paths(distance, source)
        delta = np.zeros(p)
        for w in reversed(order):
            is_valid_target = 1.0 if community_labels[w] != community_labels[source] else 0.0
            for v in predecessors[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (is_valid_target + delta[w])
            if w != source:
                betweenness[w] += delta[w]

    return betweenness / 2.0  # undirected: each pair's contribution counted from both endpoints


@dataclass(frozen=True)
class BridgeCentralityResult:
    """All four bridge-centrality measures for one weighted network and
    community assignment, each a length-p array indexed the same way as
    the weight matrix's rows."""

    strength: np.ndarray
    expected_influence: np.ndarray
    closeness: np.ndarray
    betweenness: np.ndarray


def compute_bridge_centrality(weights: np.ndarray, communities: np.ndarray) -> BridgeCentralityResult:
    """Compute `bridge_strength`, `bridge_expected_influence`,
    `bridge_closeness_centrality`, and `bridge_betweenness_centrality`
    together for one weight matrix and community assignment.

    `communities` is a length-p array (any hashable label per node) --
    caller-supplied, not computed by this function; see this module's
    own docstring for why `gopcnet` doesn't include a community-detection
    algorithm."""
    return BridgeCentralityResult(
        strength=bridge_strength(weights, communities),
        expected_influence=bridge_expected_influence(weights, communities),
        closeness=bridge_closeness_centrality(weights, communities),
        betweenness=bridge_betweenness_centrality(weights, communities),
    )
