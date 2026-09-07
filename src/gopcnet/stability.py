"""Generic bootstrap edge-stability, usable with any of this package's
four fit functions -- not just the frozen `compose_screen_then_prune`
pipeline `gopcnet.bootstrap`'s own `compute_edge_stability` is scoped
to (that module stays exactly as `docs/stage3_charter.md`'s own
archived evidence, D-019/D-020, was validated against -- unchanged and
still internal to this repository, not part of the installed package).

Bind a method's own hyperparameters yourself (`functools.partial` or a
lambda) before passing it in -- this module never needs to know about
them:

    >>> from functools import partial
    >>> import numpy as np
    >>> from gopcnet import fit_gopc
    >>> fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
    >>> result = bootstrap_edge_stability(data, fit, bootstraps=1000, rng=np.random.default_rng(0))
    >>> result.inclusion_probability  # doctest: +SKIP

Edge-weight tracking (`weight_mean`/`weight_std`) is populated only
when the fit callable's result exposes a `.weights` attribute --
`fit_gopc` and `fit_gopc_fixed_order` do (see `docs/decision_log.md`'s
D-055); the comparators `fit_ebicglasso` and `fit_pc_skeleton` don't
define an edge weight at all, so those two fields are `None` for them
and only edge-inclusion probability is computed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np


def bootstrap_resample(data: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw one nonparametric row bootstrap resample of `data` (same row count, with replacement)."""
    n = data.shape[0]
    indices = rng.integers(0, n, size=n)
    return data[indices]


class _FitResult(Protocol):
    adjacency: np.ndarray


@dataclass(frozen=True)
class EdgeStabilityResult:
    """Bootstrap edge-stability estimate for one dataset, for any fit method.

    `inclusion_probability` is the fraction of *successful* bootstrap
    resamples in which each pair was a retained edge. A resample whose
    fit raises (a degenerate, near-zero-variance resample) is excluded
    from both the numerator and the denominator, not counted as
    edge-absent -- `failed_bootstraps` records how many, rather than
    silently dropping them.

    `weight_mean`/`weight_std` are the mean/standard deviation of each
    pair's edge weight across successful resamples (0 for a resample in
    which the edge was absent, matching a standard nonparametric
    bootstrap edge-weight convention: absence contributes a weight of
    zero to the distribution, not a missing value) -- `None` if the fit
    method doesn't produce edge weights at all.
    """

    inclusion_probability: np.ndarray
    weight_mean: np.ndarray | None
    weight_std: np.ndarray | None
    successful_bootstraps: int
    failed_bootstraps: int


def bootstrap_edge_stability(
    data: np.ndarray,
    fit: Callable[[np.ndarray], _FitResult],
    *,
    bootstraps: int,
    rng: np.random.Generator,
) -> EdgeStabilityResult:
    """Run `bootstraps` row-bootstrap resamples of `data` through `fit`
    and tabulate per-pair edge-inclusion frequency (and edge-weight
    mean/std, if `fit`'s result exposes `.weights`).

    A resample on which `fit` raises `ValueError` (this package's own
    data-validation functions -- `gopcnet.screening`,
    `gopcnet.dpi.multi_conditional` -- raise `ValueError` uniformly for
    degenerate input, e.g. a zero-variance column) is treated as
    inconclusive and excluded from both the numerator and denominator,
    matching `gopcnet.bootstrap.compute_edge_stability`'s own
    convention. Any other exception propagates.
    """
    if bootstraps < 1:
        raise ValueError("bootstraps must be at least 1")
    p = data.shape[1]
    inclusion_counts = np.zeros((p, p))
    weight_sum: np.ndarray | None = None
    weight_sum_sq: np.ndarray | None = None
    successful = 0
    failed = 0

    for _ in range(bootstraps):
        resample = bootstrap_resample(data, rng)
        try:
            result = fit(resample)
        except ValueError:
            failed += 1
            continue
        adjacency = np.asarray(result.adjacency)
        inclusion_counts += adjacency
        weights = getattr(result, "weights", None)
        if weights is not None:
            weights = np.asarray(weights)
            if weight_sum is None:
                weight_sum = np.zeros((p, p))
                weight_sum_sq = np.zeros((p, p))
            weight_sum += weights
            weight_sum_sq += weights**2
        successful += 1

    if successful == 0:
        raise RuntimeError("every bootstrap resample was degenerate; cannot compute edge stability")

    weight_mean: np.ndarray | None = None
    weight_std: np.ndarray | None = None
    if weight_sum is not None and weight_sum_sq is not None:
        weight_mean = weight_sum / successful
        variance = weight_sum_sq / successful - weight_mean**2
        weight_std = np.sqrt(np.clip(variance, 0.0, None))

    return EdgeStabilityResult(
        inclusion_probability=inclusion_counts / successful,
        weight_mean=weight_mean,
        weight_std=weight_std,
        successful_bootstraps=successful,
        failed_bootstraps=failed,
    )
