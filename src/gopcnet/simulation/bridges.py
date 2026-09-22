"""Gaussian confound/bridge fixtures for the Stage 6a evidence-tier and
cross-community bridge-inference validation charter
(`docs/stage6a_charter.md`). Every shape is built from an explicit
partial-correlation edge list via `build_precision`, verified positive
definite at call time exactly as `gopcnet.simulation.motifs` verifies its
own triangle fixtures.

Every shape has two clusters, `A` and `B`, each an unstructured clique at
`RHO_WITHIN`, plus a confound node `Z` linked to one member of each
cluster at `rho_confound`. `confound_trap_observed`/`confound_trap_latent`
add a single true weak cross-cluster edge (the "bridge") between two
*other* cluster members at `rho_bridge`; `no_bridge_negative_control` adds
no bridge; `larger_clusters` uses 4-node cliques; `double_bridge` adds a
second bridge. The candidate pairs used for evaluation are always every
`A x B` pair, so most of them are decoys with a real marginal correlation
(through the confound, through the bridge, or both) but no direct edge --
see the charter's Background for why this is a nontrivial test of
conditioning-based edge evidence, not solvable by marginal correlation.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

RHO_WITHIN = 0.30
# 4-node cliques at RHO_WITHIN are not positive definite across the full
# (rho_bridge, rho_confound) grid (checked at implementation time; see the
# charter's implementation-time amendment) -- `larger_clusters` alone uses
# this reduced within-cluster strength, verified PD at every grid point.
RHO_WITHIN_LARGE_CLUSTER = 0.25

SHAPE_NAMES: tuple[str, ...] = (
    "confound_trap_observed",
    "confound_trap_latent",
    "no_bridge_negative_control",
    "larger_clusters",
    "double_bridge",
)

# Which shapes' structure actually depends on rho_bridge (the negative
# control has no bridge at all, so looping it over the bridge grid would
# just repeat identical data under a cosmetic label).
USES_BRIDGE_GRID: dict[str, bool] = {
    "confound_trap_observed": True,
    "confound_trap_latent": True,
    "no_bridge_negative_control": False,
    "larger_clusters": True,
    "double_bridge": True,
}


@dataclass(frozen=True)
class BridgeShape:
    name: str
    p: int
    edges: tuple[tuple[int, int, float], ...]
    candidates: tuple[tuple[int, int], ...]
    true_bridges: tuple[tuple[int, int], ...]
    observed: tuple[int, ...]  # column indices kept after sampling (latent-variable support)


def clique_edges(nodes: tuple[int, ...], rho: float) -> list[tuple[int, int, float]]:
    return [(i, j, rho) for i, j in itertools.combinations(nodes, 2)]


def build_precision(p: int, edges: tuple[tuple[int, int, float], ...]) -> np.ndarray:
    precision = np.eye(p)
    for i, j, rho in edges:
        precision[i, j] = precision[j, i] = -rho
    return precision


def _validate_pd(name: str, precision: np.ndarray) -> None:
    min_eig = float(np.linalg.eigvalsh(precision).min())
    if min_eig <= 0:
        raise ValueError(f"{name}: precision matrix is not positive definite (min eigenvalue {min_eig:.4f})")


def make_shape(name: str, rho_bridge: float, rho_confound: float) -> BridgeShape:
    """Build one frozen shape. `rho_bridge` is ignored (but still required,
    for a uniform call signature) when `USES_BRIDGE_GRID[name]` is False."""
    if name in ("confound_trap_observed", "confound_trap_latent"):
        a, b, z = (0, 1, 2), (3, 4, 5), 6
        edges = clique_edges(a, RHO_WITHIN) + clique_edges(b, RHO_WITHIN)
        edges += [(0, 3, rho_bridge), (2, z, rho_confound), (5, z, rho_confound)]
        candidates = tuple((i, j) for i in a for j in b)
        observed = tuple(range(7)) if name.endswith("observed") else tuple(c for c in range(7) if c != z)
        return BridgeShape(name, 7, tuple(edges), candidates, ((0, 3),), observed)

    if name == "no_bridge_negative_control":
        a, b, z = (0, 1, 2), (3, 4, 5), 6
        edges = clique_edges(a, RHO_WITHIN) + clique_edges(b, RHO_WITHIN)
        edges += [(2, z, rho_confound), (5, z, rho_confound)]
        candidates = tuple((i, j) for i in a for j in b)
        return BridgeShape(name, 7, tuple(edges), candidates, (), tuple(range(7)))

    if name == "larger_clusters":
        a, b, z = (0, 1, 2, 3), (4, 5, 6, 7), 8
        edges = clique_edges(a, RHO_WITHIN_LARGE_CLUSTER) + clique_edges(b, RHO_WITHIN_LARGE_CLUSTER)
        edges += [(0, 4, rho_bridge), (3, z, rho_confound), (7, z, rho_confound)]
        candidates = tuple((i, j) for i in a for j in b)
        return BridgeShape(name, 9, tuple(edges), candidates, ((0, 4),), tuple(range(9)))

    if name == "double_bridge":
        a, b, z = (0, 1, 2), (3, 4, 5), 6
        edges = clique_edges(a, RHO_WITHIN) + clique_edges(b, RHO_WITHIN)
        edges += [(0, 3, rho_bridge), (1, 4, rho_bridge), (2, z, rho_confound), (5, z, rho_confound)]
        candidates = tuple((i, j) for i in a for j in b)
        return BridgeShape(name, 7, tuple(edges), candidates, ((0, 3), (1, 4)), tuple(range(7)))

    raise ValueError(f"unknown Stage 6a shape: {name!r}")


def build_shape_covariance(shape: BridgeShape) -> np.ndarray:
    """Precision -> covariance for `shape`, positive-definiteness verified."""
    precision = build_precision(shape.p, shape.edges)
    _validate_pd(shape.name, precision)
    return np.linalg.inv(precision)


def sample_shape(
    shape: BridgeShape, n: int, rng: np.random.Generator, covariance: np.ndarray | None = None
) -> np.ndarray:
    """Draw `n` rows, restricted to `shape.observed` columns and sample-
    standardized (mirrors `gopcnet.simulation.motifs.sample_precision_triangle`'s
    own standardization convention)."""
    if covariance is None:
        covariance = build_shape_covariance(shape)
    full = rng.multivariate_normal(np.zeros(shape.p), covariance, size=n)
    data = full[:, list(shape.observed)]
    return (data - data.mean(axis=0)) / data.std(axis=0, ddof=1)


def observed_index(shape: BridgeShape, original_column: int) -> int:
    return shape.observed.index(original_column)


def observed_candidates(shape: BridgeShape) -> tuple[tuple[int, int], ...]:
    """Candidate pairs re-indexed into the observed (post-latent-drop)
    column space; a pair naming a dropped column is skipped."""
    lookup = {orig: k for k, orig in enumerate(shape.observed)}
    return tuple((lookup[i], lookup[j]) for i, j in shape.candidates if i in lookup and j in lookup)


def observed_true_bridges(shape: BridgeShape) -> tuple[tuple[int, int], ...]:
    lookup = {orig: k for k, orig in enumerate(shape.observed)}
    return tuple((lookup[i], lookup[j]) for i, j in shape.true_bridges if i in lookup and j in lookup)
