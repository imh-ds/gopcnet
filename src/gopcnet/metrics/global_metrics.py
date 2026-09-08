"""Whole-network summary statistics -- distinct from every other module
in `gopcnet.metrics`/`gopcnet.stability`, which all describe an
individual edge or node, never the network as a single number.

Operates on the same two matrix shapes the rest of the package already
produces: a boolean, symmetric, zero-diagonal adjacency matrix (from
any of the four fit functions), and a signed, symmetric, zero-diagonal
weight matrix (`GOPCResult.weights`, `EdgeStabilityResult.weight_mean`,
or your own). The two are taken as independent arguments rather than
one being derived from the other -- consistent with
`fit_gaussian_graphical_model`'s own `data`/`adjacency` split -- since
not every weight matrix in this package (e.g. a bootstrap
`weight_mean`) is guaranteed to be exactly zero everywhere `adjacency`
says an edge is absent.

Four measures, each independently exported and bundled by
`compute_global_metrics`:

- `density`: proportion of possible edges present (from `adjacency`).
- `global_strength`: sum of `|weight|` over all edges -- bootnet's own
  "global strength," the summary statistic its network comparison test
  (NCT) checks for invariance between two networks.
- `global_clustering_coefficient`: transitivity -- the fraction of
  connected triples of nodes that close into a triangle, computed from
  the *binary* `adjacency`, not the weights (see that function's own
  docstring for why).
- `average_shortest_path_length`: mean geodesic distance over every
  reachable pair, using the same `1 / |weight|` distance convention
  `gopcnet.metrics.centrality` already uses for closeness/betweenness.

See `docs/decision_log.md`'s D-061 for the conventions and why
small-worldness was deliberately left out of this first pass.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .centrality import _dijkstra_with_paths, _distance_matrix, _validate_weights


def _validate_adjacency(adjacency: np.ndarray) -> np.ndarray:
    values = np.asarray(adjacency, dtype=bool)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("adjacency must be a square matrix")
    if not np.array_equal(values, values.T):
        raise ValueError("adjacency must be symmetric")
    if np.any(np.diag(values)):
        raise ValueError("adjacency must have a False diagonal")
    return values


def density(adjacency: np.ndarray) -> float:
    """Proportion of possible edges present: `n_edges / (p * (p - 1) / 2)`.

    `nan` for a single-node network (no possible edges to have a
    proportion of)."""
    values = _validate_adjacency(adjacency)
    p = values.shape[0]
    total_pairs = p * (p - 1) // 2
    if total_pairs == 0:
        return float("nan")
    n_edges = int(np.triu(values, k=1).sum())
    return n_edges / total_pairs


def global_strength(weights: np.ndarray) -> float:
    """Sum of `|weight|` over every edge, each counted once (upper
    triangle only) -- bootnet's own "global strength": the statistic
    its network comparison test (NCT) checks for invariance between two
    networks' overall level of connectivity, as distinct from any one
    edge or node."""
    values = _validate_weights(weights)
    return float(np.abs(np.triu(values, k=1)).sum())


def global_clustering_coefficient(adjacency: np.ndarray) -> float:
    """Global clustering coefficient (transitivity): the fraction of
    connected triples of nodes -- one node linked to an unordered pair
    of others, whether or not that pair is itself linked -- that are
    fully closed into a triangle.

    Computed from the *binary* `adjacency`, not a weighted variant.
    Weighted clustering coefficients exist (e.g. Zhang & Horvath, 2005;
    Onnela et al., 2005) but disagree with each other on how to combine
    signed weights into a single per-triple magnitude, with no
    consensus convention the way `1 / |weight|` distance has for
    closeness/betweenness -- the plain binary definition is used here
    to avoid picking one silently.

    Uses the standard identity `3 * n_triangles / n_connected_triples`,
    computed via `trace(A^3) / 2` for the numerator (each triangle
    contributes `6` to `trace(A^3)`, and the `3 *` and `1/6` cancel to
    `1/2`) and `sum_v C(deg(v), 2)` for the denominator. `nan` if the
    network has no connected triples at all (e.g. at most one edge).
    """
    values = _validate_adjacency(adjacency)
    adjacency_float = values.astype(float)
    degree = adjacency_float.sum(axis=1)
    connected_triples = float(np.sum(degree * (degree - 1.0) / 2.0))
    if connected_triples == 0.0:
        return float("nan")
    closed_triples = float(np.trace(adjacency_float @ adjacency_float @ adjacency_float)) / 2.0
    return closed_triples / connected_triples


def average_shortest_path_length(weights: np.ndarray) -> float:
    """Mean geodesic distance (`1 / |weight|` per edge, the same
    convention `closeness_centrality`/`betweenness_centrality` use)
    over every reachable pair of nodes.

    Unreachable pairs (disconnected components) are excluded from both
    the sum and the count, matching `closeness_centrality`'s own
    reachability-only convention rather than treating an infinite
    distance as a large finite one. `nan` if no pair is reachable at
    all (e.g. an edgeless network)."""
    values = _validate_weights(weights)
    distance = _distance_matrix(values)
    p = distance.shape[0]
    total = 0.0
    count = 0
    for source in range(p):
        dist, _sigma, _predecessors, _order = _dijkstra_with_paths(distance, source)
        for target in range(source + 1, p):
            if np.isfinite(dist[target]):
                total += dist[target]
                count += 1
    if count == 0:
        return float("nan")
    return total / count


@dataclass(frozen=True)
class GlobalMetricsResult:
    """All four whole-network summary statistics together, for one
    adjacency matrix and (possibly different) weight matrix."""

    density: float
    global_strength: float
    clustering_coefficient: float
    average_shortest_path_length: float


def compute_global_metrics(adjacency: np.ndarray, weights: np.ndarray) -> GlobalMetricsResult:
    """Compute `density`, `global_strength`, `global_clustering_coefficient`,
    and `average_shortest_path_length` together.

    `adjacency` and `weights` must be the same shape but are otherwise
    independent (see this module's own docstring for why) -- typically
    `result.adjacency` and `result.weights` from the same `fit_gopc`/
    `fit_gopc_fixed_order` call, but not required to come from the same
    fit."""
    adjacency_values = _validate_adjacency(adjacency)
    weight_values = _validate_weights(weights)
    if adjacency_values.shape != weight_values.shape:
        raise ValueError("adjacency and weights must have the same shape")
    return GlobalMetricsResult(
        density=density(adjacency_values),
        global_strength=global_strength(weight_values),
        clustering_coefficient=global_clustering_coefficient(adjacency_values),
        average_shortest_path_length=average_shortest_path_length(weight_values),
    )
