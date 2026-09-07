"""Node centrality measures for a weighted network.

Operates on any signed, symmetric, zero-diagonal weight matrix -- the
same shape `gopcnet.pipeline.gopc.GOPCResult.weights` and
`gopcnet.stability.EdgeStabilityResult.weight_mean` already produce
(see `docs/decision_log.md`'s D-055 for what a GOPC edge's weight
means). Not specific to GOPC -- any weighted adjacency matrix of this
shape works, including a comparator's own weights if you construct
one (`fit_ebicglasso`/`fit_pc_skeleton` don't provide one out of the
box).

`closeness_centrality` and `betweenness_centrality` both need a
*distance*, not a weight, for each edge; following the qgraph/bootnet
convention, distance is `1 / |weight|` -- a stronger association
(regardless of sign) is a shorter, more direct connection. Sign still
matters for `expected_influence` (which sums signed weight) but not
for the two path-based measures, since a negative and a positive
association of the same magnitude are equally "close." This is a
convention, not a neutral default -- see each function's own
docstring.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np


def _validate_weights(weights: np.ndarray) -> np.ndarray:
    values = np.asarray(weights, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("weights must be a square matrix")
    if not np.allclose(values, values.T):
        raise ValueError("weights must be symmetric")
    if not np.allclose(np.diag(values), 0.0):
        raise ValueError("weights must have a zero diagonal")
    return values


def strength(weights: np.ndarray) -> np.ndarray:
    """Unsigned strength centrality: sum of `|weight|` over each node's edges."""
    values = _validate_weights(weights)
    return np.abs(values).sum(axis=1)


def expected_influence(weights: np.ndarray) -> np.ndarray:
    """Expected influence (Robinaugh, Millner, & McNally, 2016): signed
    sum of edge weight for each node. Unlike `strength`, a node whose
    edges are mostly negative gets a negative score -- captures net,
    not absolute, influence on the rest of the network."""
    values = _validate_weights(weights)
    return values.sum(axis=1)


def _distance_matrix(weights: np.ndarray) -> np.ndarray:
    """`1 / |weight|` per edge; `np.inf` where there is no edge (weight == 0)."""
    magnitude = np.abs(weights)
    with np.errstate(divide="ignore"):
        distance = np.where(magnitude > 0.0, 1.0 / magnitude, np.inf)
    np.fill_diagonal(distance, 0.0)
    return distance


def _dijkstra_with_paths(
    distance: np.ndarray, source: int
) -> tuple[np.ndarray, np.ndarray, list[list[int]], list[int]]:
    """Single-source shortest paths from `source` (Dijkstra), also
    returning `sigma` (shortest-path counts) and each node's
    shortest-path predecessors -- the two extra pieces Brandes'
    betweenness algorithm needs beyond plain distances."""
    p = distance.shape[0]
    dist = np.full(p, np.inf)
    dist[source] = 0.0
    sigma = np.zeros(p)
    sigma[source] = 1.0
    predecessors: list[list[int]] = [[] for _ in range(p)]
    visited = np.zeros(p, dtype=bool)
    order: list[int] = []
    heap: list[tuple[float, int]] = [(0.0, source)]
    tolerance = 1e-12

    while heap:
        d, u = heapq.heappop(heap)
        if visited[u]:
            continue
        visited[u] = True
        order.append(u)
        for v in range(p):
            if u == v or not np.isfinite(distance[u, v]):
                continue
            candidate = d + distance[u, v]
            if candidate < dist[v] - tolerance:
                dist[v] = candidate
                sigma[v] = sigma[u]
                predecessors[v] = [u]
                heapq.heappush(heap, (candidate, v))
            elif abs(candidate - dist[v]) <= tolerance:
                sigma[v] += sigma[u]
                predecessors[v].append(u)

    return dist, sigma, predecessors, order


def closeness_centrality(weights: np.ndarray) -> np.ndarray:
    """Closeness centrality: the reciprocal of the sum of shortest-path
    distances (`1 / |weight|` per edge) from a node to every other node
    it can reach. A node with no path to any other node (isolated, or
    stranded in its own disconnected component of size 1) gets `0.0`,
    matching qgraph's own convention -- reachability, not global
    connectivity, is what's actually required."""
    values = _validate_weights(weights)
    distance = _distance_matrix(values)
    p = distance.shape[0]
    closeness = np.zeros(p)
    for s in range(p):
        dist, _sigma, _predecessors, _order = _dijkstra_with_paths(distance, s)
        reachable = np.isfinite(dist) & (np.arange(p) != s)
        total = dist[reachable].sum()
        closeness[s] = 1.0 / total if total > 0 else 0.0
    return closeness


def betweenness_centrality(weights: np.ndarray) -> np.ndarray:
    """Betweenness centrality (Brandes, 2001): for every pair of other
    nodes, the fraction of their shortest paths (`1 / |weight|` per
    edge) that pass through this node, summed over all pairs. Ties
    (multiple shortest paths of equal length between the same pair) are
    split proportionally, not resolved to an arbitrary single path --
    the full Brandes accumulation, not a naive single-shortest-path
    count. Unreachable pairs contribute nothing."""
    values = _validate_weights(weights)
    distance = _distance_matrix(values)
    p = distance.shape[0]
    betweenness = np.zeros(p)

    for s in range(p):
        _dist, sigma, predecessors, order = _dijkstra_with_paths(distance, s)
        delta = np.zeros(p)
        for w in reversed(order):
            for v in predecessors[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                betweenness[w] += delta[w]

    return betweenness / 2.0  # undirected: each pair's contribution counted from both endpoints


@dataclass(frozen=True)
class CentralityResult:
    """All four centrality measures for one weighted network, each a
    length-p array indexed the same way as the weight matrix's rows."""

    strength: np.ndarray
    expected_influence: np.ndarray
    closeness: np.ndarray
    betweenness: np.ndarray


def compute_centrality(weights: np.ndarray) -> CentralityResult:
    """Compute `strength`, `expected_influence`, `closeness_centrality`,
    and `betweenness_centrality` together for one weight matrix."""
    return CentralityResult(
        strength=strength(weights),
        expected_influence=expected_influence(weights),
        closeness=closeness_centrality(weights),
        betweenness=betweenness_centrality(weights),
    )
