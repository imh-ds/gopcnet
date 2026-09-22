"""Psychology-like Gaussian graphical models with known ground truth.

Every earlier benchmark in this repository used a handful of fixed motif
shapes. The composed `p = 15` networks contain pure-noise columns that
are independent of everything, which psychological item sets almost
never have. These generators draw a *random* sparse partial-correlation
network per replicate, from families common in the network-psychometrics
simulation literature:

- `random_sparse`, `random_dense`: Erdos-Renyi at densities .20 and .35
- `small_world`: Watts-Strogatz, `k = 4`, rewiring .1
- `clustered`: a stochastic block model, roughly symptom clusters or
  scales
- `random_with_isolates`: Erdos-Renyi at .20 on 75% of the nodes plus 25%
  isolated nodes, which re-creates the legacy "noise column" regime as a
  manipulated factor instead of a hidden one

Edge weights mix weak and strong partial correlations (70% in
`[.08, .20]`, 30% in `[.20, .40]`), with 15% negative. The weighted
matrix is scaled down only as far as needed for the precision matrix
`I - P` to be positive definite with a margin (smallest eigenvalue
`>= .1`), so the realized partial correlations `P` are known exactly.

Everything samples through `gopcnet.generators.sampling` (Cholesky;
D-067). Designed for Stage 7b
(`docs/development_plan/phase1_external_validity.md`, step 1.6). Once a
charter has used this module, treat the existing structures as frozen:
add new functions or structure names, never alter these.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

import numpy as np

from gopcnet.generators.sampling import covariance_from_precision, sample_gaussian

WEAK_EDGE_RANGE: tuple[float, float] = (0.08, 0.20)
STRONG_EDGE_RANGE: tuple[float, float] = (0.20, 0.40)
STRONG_EDGE_PROBABILITY = 0.30
NEGATIVE_EDGE_PROBABILITY = 0.15
MIN_PRECISION_EIGENVALUE = 0.10


# --- graph generators (boolean, symmetric, zero diagonal) -----------------


def erdos_renyi(p: int, density: float, rng: np.random.Generator) -> np.ndarray:
    """Each pair is an edge independently with probability `density`."""
    upper = np.triu(rng.random((p, p)) < density, k=1)
    return upper | upper.T


def watts_strogatz(p: int, k: int, rewire: float, rng: np.random.Generator) -> np.ndarray:
    """Ring lattice with `k` nearest neighbors (`k / 2` on each side); each
    lattice edge `(i, i + s)` is rewired with probability `rewire` to a
    uniformly chosen node that is not already a neighbor of `i`. The
    edge count is preserved."""
    if k % 2 or not (0 < k < p):
        raise ValueError("k must be even and 0 < k < p")
    adjacency = np.zeros((p, p), dtype=bool)
    for i in range(p):
        for step in range(1, k // 2 + 1):
            j = (i + step) % p
            adjacency[i, j] = adjacency[j, i] = True
    for step in range(1, k // 2 + 1):
        for i in range(p):
            j = (i + step) % p
            if not adjacency[i, j] or rng.random() >= rewire:
                continue
            candidates = [c for c in range(p) if c != i and not adjacency[i, c]]
            if not candidates:
                continue
            target = candidates[int(rng.integers(len(candidates)))]
            adjacency[i, j] = adjacency[j, i] = False
            adjacency[i, target] = adjacency[target, i] = True
    return adjacency


def stochastic_block(
    p: int, n_blocks: int, p_within: float, p_between: float, rng: np.random.Generator
) -> np.ndarray:
    """Nodes split into `n_blocks` near-equal consecutive blocks; pairs
    connect with probability `p_within` inside a block and `p_between`
    across blocks."""
    labels = np.empty(p, dtype=int)
    for block, members in enumerate(np.array_split(np.arange(p), n_blocks)):
        labels[members] = block
    same = labels[:, None] == labels[None, :]
    probability = np.where(same, p_within, p_between)
    upper = np.triu(rng.random((p, p)) < probability, k=1)
    return upper | upper.T


def with_isolates(
    build: Callable[[int, np.random.Generator], np.ndarray],
    p: int,
    isolate_fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Build a graph on `p - round(isolate_fraction * p)` nodes, append
    isolated nodes, and randomly permute the node order (so isolates are
    not always the last columns)."""
    n_isolated = int(round(isolate_fraction * p))
    core = build(p - n_isolated, rng)
    adjacency = np.zeros((p, p), dtype=bool)
    adjacency[: p - n_isolated, : p - n_isolated] = core
    order = rng.permutation(p)
    return adjacency[np.ix_(order, order)]


# --- weights and the precision matrix -------------------------------------


def draw_edge_weights(adjacency: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Signed intended partial correlations on `adjacency`'s edges: a
    weak/strong magnitude mixture with a fixed share of negative edges."""
    p = adjacency.shape[0]
    rows, cols = np.nonzero(np.triu(adjacency, k=1))
    strong = rng.random(len(rows)) < STRONG_EDGE_PROBABILITY
    magnitude = np.where(
        strong,
        rng.uniform(*STRONG_EDGE_RANGE, size=len(rows)),
        rng.uniform(*WEAK_EDGE_RANGE, size=len(rows)),
    )
    sign = np.where(rng.random(len(rows)) < NEGATIVE_EDGE_PROBABILITY, -1.0, 1.0)
    weights = np.zeros((p, p))
    weights[rows, cols] = magnitude * sign
    return weights + weights.T


def scale_to_positive_definite(weights: np.ndarray) -> tuple[np.ndarray, float]:
    """Return `(c * weights, c)` with `c = min(1, (1 - margin) / lambda_max)`,
    so `I - c * weights` has smallest eigenvalue `>= MIN_PRECISION_EIGENVALUE`.
    With a unit-diagonal precision `K = I - P`, the partial correlations are
    exactly `P`."""
    lam_max = float(np.linalg.eigvalsh(weights).max()) if weights.size else 0.0
    shrinkage = 1.0 if lam_max <= 0 else min(1.0, (1.0 - MIN_PRECISION_EIGENVALUE) / lam_max)
    return shrinkage * weights, shrinkage


# --- registry --------------------------------------------------------------


def _random_sparse(p: int, rng: np.random.Generator) -> np.ndarray:
    return erdos_renyi(p, 0.20, rng)


def _random_dense(p: int, rng: np.random.Generator) -> np.ndarray:
    return erdos_renyi(p, 0.35, rng)


def _small_world(p: int, rng: np.random.Generator) -> np.ndarray:
    return watts_strogatz(p, 4, 0.1, rng)


def _clustered(p: int, rng: np.random.Generator) -> np.ndarray:
    return stochastic_block(p, max(2, round(p / 5)), 0.6, 0.05, rng)


def _random_with_isolates(p: int, rng: np.random.Generator) -> np.ndarray:
    return with_isolates(_random_sparse, p, 0.25, rng)


_GRAPH_BUILDERS: dict[str, Callable[[int, np.random.Generator], np.ndarray]] = {
    "random_sparse": _random_sparse,
    "random_dense": _random_dense,
    "small_world": _small_world,
    "clustered": _clustered,
    "random_with_isolates": _random_with_isolates,
}

STRUCTURES: tuple[str, ...] = tuple(_GRAPH_BUILDERS)


@dataclass(frozen=True)
class PsychTruth:
    """One ground-truth network.

    - `adjacency`: the true edges.
    - `partial_correlations`: the realized partial correlations `P`
      (zero diagonal).
    - `correlation`: the model-implied correlation matrix (unit
      diagonal).
    - `shrinkage`: the positive-definiteness scaling `c` applied to the
      drawn weights. Denser graphs shrink more; report it, so shrinkage
      is never mistaken for a method effect.
    - `truth_hash`: the first 16 hex digits of the SHA-256 of
      `P.round(12)`, used to check pairing across sample sizes.
    """

    structure: str
    adjacency: np.ndarray
    partial_correlations: np.ndarray
    correlation: np.ndarray
    shrinkage: float
    truth_hash: str


def make_truth(structure: str, p: int, rng: np.random.Generator) -> PsychTruth:
    """Draw one ground-truth network of the named structure family."""
    try:
        build = _GRAPH_BUILDERS[structure]
    except KeyError as exc:
        raise ValueError(f"unknown structure {structure!r}; expected one of {STRUCTURES}") from exc
    if int(p) != p or p < 4:
        raise ValueError("p must be an integer of at least 4")
    adjacency = build(int(p), rng)
    partial, shrinkage = scale_to_positive_definite(draw_edge_weights(adjacency, rng))
    precision = np.eye(int(p)) - partial
    covariance = covariance_from_precision(precision)
    scale = np.sqrt(np.diag(covariance))
    correlation = covariance / np.outer(scale, scale)
    correlation = (correlation + correlation.T) / 2.0
    np.fill_diagonal(correlation, 1.0)
    digest = hashlib.sha256(np.ascontiguousarray(partial.round(12)).tobytes()).hexdigest()[:16]
    return PsychTruth(
        structure=structure,
        adjacency=adjacency,
        partial_correlations=partial,
        correlation=correlation,
        shrinkage=shrinkage,
        truth_hash=digest,
    )


def sample_data(truth: PsychTruth, n: int, rng: np.random.Generator) -> np.ndarray:
    """Draw `n` rows from `N(0, truth.correlation)` via the Cholesky sampler."""
    return sample_gaussian(truth.correlation, n, rng)
