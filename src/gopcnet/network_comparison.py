"""Network comparison test (NCT; van Borkulo et al., 2017) -- bootnet's
own procedure for testing whether two networks, each estimated from an
independent sample, differ more than their own sampling error would
predict.

Unlike everything in `gopcnet.stability`, which asks how reliable
*one* network's own estimate is, `network_comparison_test` asks a
between-groups question: are two samples' networks different enough to
say the groups themselves differ, or is the difference within the
noise either group's own estimate would show on its own?

Two test statistics, both from the NCT literature:

- `global_strength_difference`: `|global_strength(A) - global_strength(B)|`
  -- `gopcnet.metrics.global_metrics.global_strength` (D-061's own
  definition, reused directly here) -- do the two networks differ in
  their overall level of connectivity?
- `max_edge_weight_difference`: the largest absolute difference between
  any one corresponding edge weight across the two networks -- do the
  two networks differ in structure, even where overall connectivity is
  similar?

Both are tested by the same permutation procedure: pool the two
samples, repeatedly re-split the pooled sample at random into two
groups of the same sizes as the real groups (*permuting group
membership*, not resampling with replacement -- a genuinely different
resampling scheme from every bootstrap in `gopcnet.stability`), refit
both groups' networks under each re-split, and see how often a random
re-split produces a difference at least as large as the one actually
observed. See `docs/decision_log.md`'s D-062 for the exact conventions
(add-one p-value smoothing, which fit methods this applies to, and
what "same variables" means across the two samples).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from gopcnet.metrics.global_metrics import global_strength


class _WeightedFitResult(Protocol):
    weights: np.ndarray | None


def _extract_weights(result: _WeightedFitResult) -> np.ndarray:
    weights = getattr(result, "weights", None)
    if weights is None:
        raise ValueError(
            "network_comparison_test requires a fit method whose result exposes edge "
            "weights (fit_gopc or fit_gopc_fixed_order); comparators like "
            "fit_ebicglasso/fit_pc_skeleton don't define one"
        )
    return np.asarray(weights)


def _max_edge_weight_difference(weights_a: np.ndarray, weights_b: np.ndarray) -> float:
    p = weights_a.shape[0]
    if p < 2:
        return 0.0
    upper = np.triu_indices(p, k=1)
    return float(np.max(np.abs(weights_a[upper] - weights_b[upper])))


@dataclass(frozen=True)
class NetworkComparisonResult:
    """Network comparison test (NCT) output for two independent samples.

    `observed_global_strength_difference`/`observed_max_edge_weight_difference`
    are computed from `fit` applied to `data_a`/`data_b` directly (not
    from the permutation null). `global_strength_p_value`/
    `max_edge_weight_difference_p_value` are the fraction of successful
    permutations whose own statistic was at least as large as the
    observed one, with add-one smoothing (Phipson & Smyth, 2010) so a
    p-value is never reported as exactly zero. A *small* p-value is
    evidence the two groups' networks genuinely differ; a large one
    means the observed difference is within what random group
    membership alone would produce.

    `permutation_global_strength_differences`/
    `permutation_max_edge_weight_differences` are the raw per-permutation
    null-distribution values, for a caller who wants to inspect or
    re-summarize them directly (e.g. plot the null distribution against
    the observed statistic).
    """

    observed_global_strength_difference: float
    global_strength_p_value: float
    observed_max_edge_weight_difference: float
    max_edge_weight_difference_p_value: float
    permutation_global_strength_differences: np.ndarray
    permutation_max_edge_weight_differences: np.ndarray
    successful_permutations: int
    failed_permutations: int


def network_comparison_test(
    data_a: np.ndarray,
    data_b: np.ndarray,
    fit: Callable[[np.ndarray], _WeightedFitResult],
    *,
    permutations: int,
    rng: np.random.Generator,
) -> NetworkComparisonResult:
    """Test whether `data_a` and `data_b`'s networks differ more than
    sampling error alone would predict.

    Parameters
    ----------
    data_a, data_b : np.ndarray
        Two independent samples over the **same variables in the same
        column order** -- rows need not match in count between the two,
        but `data_a.shape[1]` must equal `data_b.shape[1]` and both must
        mean the same thing column-for-column (this is on the caller;
        nothing here can verify it).
    fit : Callable[[np.ndarray], _WeightedFitResult]
        `fit_gopc` or `fit_gopc_fixed_order`, with hyperparameters
        already bound via `functools.partial` -- the same convention
        `bootstrap_edge_stability` and friends use. Must return a
        result exposing `.weights` (the comparators
        `fit_ebicglasso`/`fit_pc_skeleton` don't define one and will
        raise).
    permutations : int
        Number of random re-splits of the pooled sample used to build
        the null distribution.
    rng : np.random.Generator
        Controls the permutations.

    Returns
    -------
    NetworkComparisonResult

    Examples
    --------
    >>> import numpy as np
    >>> from functools import partial
    >>> from gopcnet import fit_gopc
    >>> from gopcnet.comparison import network_comparison_test
    >>> fit = partial(fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)
    >>> result = network_comparison_test(
    ...     data_a, data_b, fit, permutations=1000, rng=np.random.default_rng(0),
    ... )  # doctest: +SKIP
    >>> result.global_strength_p_value, result.max_edge_weight_difference_p_value  # doctest: +SKIP
    """
    values_a = np.asarray(data_a, dtype=float)
    values_b = np.asarray(data_b, dtype=float)
    if values_a.ndim != 2 or values_b.ndim != 2:
        raise ValueError("data_a and data_b must both be two-dimensional arrays")
    if values_a.shape[1] != values_b.shape[1]:
        raise ValueError("data_a and data_b must have the same number of columns")
    if permutations < 1:
        raise ValueError("permutations must be at least 1")

    weights_a = _extract_weights(fit(values_a))
    weights_b = _extract_weights(fit(values_b))

    observed_global_strength_difference = abs(global_strength(weights_a) - global_strength(weights_b))
    observed_max_edge_weight_difference = _max_edge_weight_difference(weights_a, weights_b)

    n_a = values_a.shape[0]
    pooled = np.vstack([values_a, values_b])
    n = pooled.shape[0]

    permutation_global_strength_differences: list[float] = []
    permutation_max_edge_weight_differences: list[float] = []
    failed = 0

    for _ in range(permutations):
        permuted_indices = rng.permutation(n)
        permuted_a = pooled[permuted_indices[:n_a]]
        permuted_b = pooled[permuted_indices[n_a:]]
        try:
            permuted_weights_a = _extract_weights(fit(permuted_a))
            permuted_weights_b = _extract_weights(fit(permuted_b))
        except ValueError:
            failed += 1
            continue
        permutation_global_strength_differences.append(
            abs(global_strength(permuted_weights_a) - global_strength(permuted_weights_b))
        )
        permutation_max_edge_weight_differences.append(
            _max_edge_weight_difference(permuted_weights_a, permuted_weights_b)
        )

    successful = len(permutation_global_strength_differences)
    if successful == 0:
        raise RuntimeError("every permutation was degenerate; cannot compute the network comparison test")

    permutation_global_strength_array = np.array(permutation_global_strength_differences)
    permutation_max_edge_array = np.array(permutation_max_edge_weight_differences)

    # Add-one smoothing (Phipson & Smyth, 2010): the observed statistic is
    # itself one draw from the same permutation-null-consistent process, so
    # a permutation p-value should never be reported as exactly zero.
    global_strength_p_value = (
        int(np.sum(permutation_global_strength_array >= observed_global_strength_difference)) + 1
    ) / (successful + 1)
    max_edge_weight_difference_p_value = (
        int(np.sum(permutation_max_edge_array >= observed_max_edge_weight_difference)) + 1
    ) / (successful + 1)

    return NetworkComparisonResult(
        observed_global_strength_difference=observed_global_strength_difference,
        global_strength_p_value=global_strength_p_value,
        observed_max_edge_weight_difference=observed_max_edge_weight_difference,
        max_edge_weight_difference_p_value=max_edge_weight_difference_p_value,
        permutation_global_strength_differences=permutation_global_strength_array,
        permutation_max_edge_weight_differences=permutation_max_edge_array,
        successful_permutations=successful,
        failed_permutations=failed,
    )
