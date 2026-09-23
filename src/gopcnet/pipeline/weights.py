"""Edge-weight annotation for GOPC's two variants.

`gopcnet.pipeline.compose.compose_screen_then_prune` and
`gopcnet.pipeline.growing_subset_dpi.growing_subset_dpi` -- the frozen
mechanisms this package's own archived evidence was validated against
-- decide retain/prune with a partial-correlation *p-value* and discard
the partial-correlation *value* itself. This module recovers a signed
edge weight for each retained edge without changing either mechanism's
decision logic: it consumes their existing outputs (the screened
candidate graph, and, for fixed-order, the component shape descriptors
they already compute) and re-runs the same conditioning tests purely
to read off `partial_correlation`, never `p_value`. See
`docs/decision_log.md`'s D-055 for the convention and its rationale.

Convention, by variant:

- Untested edges (no DPI conditioning ever ran -- an isolated pair, or
  a passed-through non-validated-shape component): weight is the raw,
  unconditional Pearson correlation from screening.
- Fixed-order GOPC: exactly one conditioning test decided the edge (on
  every other member of its clique); weight is that test's own
  partial correlation.
- Growing-order GOPC: many subsets were tested (retention requires
  *every* tested subset, across every size up to the one that decided
  the edge, to reject independence); weight is the minimum-magnitude
  partial correlation among all of them, sign preserved -- the
  weakest surviving evidence for the edge, matching what the retain
  rule itself actually guarantees.

Weights are zero wherever the corresponding adjacency entry is False,
so `weights` and `adjacency` always agree on which edges exist.
"""

from __future__ import annotations

import warnings
from itertools import combinations

import numpy as np

from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence
from gopcnet.metrics.fit import _fit_constrained_precision
from gopcnet.pipeline.compose import connected_components
from gopcnet.screening import compute_pairwise_screening_evidence


def _marginal_correlation_matrix(data: np.ndarray) -> np.ndarray:
    return compute_pairwise_screening_evidence(data).correlation


def compute_fixed_order_weights(
    data: np.ndarray,
    adjacency: np.ndarray,
    shapes: dict[frozenset[int], dict[str, object]],
) -> np.ndarray:
    """Edge weights for `fit_gopc_fixed_order`'s output.

    `shapes` must be the exact second return value of the
    `compose_screen_then_prune` call that produced `adjacency` -- reused
    as-is, not recomputed, so this can never disagree with that call
    about which components were validated-shape cliques.
    """
    weights = _marginal_correlation_matrix(data)

    for component, shape in shapes.items():
        if not shape["is_validated_shape"]:
            continue
        nodes = sorted(component)
        for i, j in combinations(nodes, 2):
            conditioning = [k for k in nodes if k not in (i, j)]
            evidence = compute_partial_correlation_evidence(data, i, j, conditioning)
            weights[i, j] = weights[j, i] = evidence.partial_correlation

    mask = adjacency.astype(bool)
    weights = np.where(mask, weights, 0.0)
    np.fill_diagonal(weights, 0.0)
    return weights


def compute_growing_order_weights(
    data: np.ndarray,
    adjacency: np.ndarray,
    flagged: np.ndarray,
    conditioning_size_used: dict[tuple[int, int], int],
    *,
    max_conditioning_size: int,
) -> np.ndarray:
    """Edge weights for `fit_gopc`'s (growing-order) output.

    `flagged` (the screened candidate graph) and `conditioning_size_used`
    must come from the exact `growing_subset_dpi` call that produced
    `adjacency` -- reused as-is, so the set of subsets re-tested here to
    read off a weight is always exactly the set that call already
    evaluated to make its own retain decision.
    """
    p = adjacency.shape[0]
    weights = _marginal_correlation_matrix(data)

    node_to_component: dict[int, frozenset[int]] = {}
    for component in connected_components(flagged):
        for node in component:
            node_to_component[node] = component

    for i in range(p):
        for j in range(i + 1, p):
            if not adjacency[i, j]:
                continue
            reached_size = conditioning_size_used.get((i, j), 0)
            if reached_size == 0:
                continue  # untested (isolated pair): marginal correlation already in place
            component = node_to_component.get(i, frozenset())
            pool = sorted(component - {i, j})
            cap = min(len(pool), max_conditioning_size, reached_size)

            observed: list[float] = []
            for size in range(1, cap + 1):
                for subset in combinations(pool, size):
                    try:
                        evidence = compute_partial_correlation_evidence(data, i, j, subset)
                    except ValueError:
                        continue
                    observed.append(evidence.partial_correlation)

            if observed:
                weakest = min(observed, key=abs)
                weights[i, j] = weights[j, i] = weakest

    mask = adjacency.astype(bool)
    weights = np.where(mask, weights, 0.0)
    np.fill_diagonal(weights, 0.0)
    return weights


def refit_weights_from_correlation(
    corr: np.ndarray, adjacency: np.ndarray, *, max_iter: int = 100, tol: float = 1e-6
) -> np.ndarray:
    """Partial correlations from the constrained maximum-likelihood GGM
    on `adjacency`'s support: `-K_ij / sqrt(K_ii K_jj)` for the fitted
    precision `K`, zero off the support.

    This is the quantity psychology readers usually take an edge weight
    to mean: the partial correlation controlling for *all* other
    variables, given the selected structure. The default D-055 weights
    are instead the smallest-magnitude low-order partial correlation
    among the tested sets.

    The fit is the same covariance-selection algorithm as
    `gopcnet.metrics.fit.fit_gaussian_graphical_model` (iterative
    proportional scaling). Partial correlations are scale-invariant, so
    a correlation matrix gives the same result as a covariance matrix.
    Warns if the fit does not converge within `max_iter`.
    """
    matrix = np.asarray(corr, dtype=float)
    support = np.asarray(adjacency, dtype=bool)
    p = matrix.shape[0]
    if matrix.shape != (p, p) or support.shape != (p, p):
        raise ValueError("corr and adjacency must be matching square matrices")
    if not np.array_equal(support, support.T) or np.diag(support).any():
        raise ValueError("adjacency must be symmetric with a False diagonal")
    precision, _, converged, _ = _fit_constrained_precision(matrix, support, max_iter=max_iter, tol=tol)
    if not converged:
        warnings.warn(
            f"constrained GGM fit did not converge within {max_iter} iterations; refit weights are approximate",
            RuntimeWarning,
            stacklevel=2,
        )
    scale = np.sqrt(np.diag(precision))
    partial = -precision / np.outer(scale, scale)
    partial = (partial + partial.T) / 2.0
    weights = np.where(support, partial, 0.0)
    np.fill_diagonal(weights, 0.0)
    return weights


def refit_weights(data: np.ndarray, adjacency: np.ndarray, *, max_iter: int = 100, tol: float = 1e-6) -> np.ndarray:
    """`refit_weights_from_correlation` on the data's Pearson correlation
    matrix. Requires more rows than columns."""
    values = np.asarray(data, dtype=float)
    if values.ndim != 2:
        raise ValueError("data must be a two-dimensional array")
    if values.shape[0] <= values.shape[1]:
        raise ValueError("data must have more rows than columns for the constrained MLE")
    return refit_weights_from_correlation(np.corrcoef(values, rowvar=False), adjacency, max_iter=max_iter, tol=tol)
