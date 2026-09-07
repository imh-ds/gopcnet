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

This module also provides `case_drop_bootstrap`/`cs_coefficient`, a
second, different kind of bootstrap: instead of resampling *with*
replacement at the full sample size to ask how stable a specific
edge is, it *subsamples without* replacement at shrinking sample
sizes to ask how much of the sample could be thrown away before a
statistic (typically a centrality measure) stops resembling the
full-sample estimate at all -- the correlation-stability (CS)
coefficient from Epskamp, Borsboom, & Fried (2018). See
`docs/decision_log.md`'s D-056 for the exact convention this
implementation follows.

A third capability, `bootstrap_replicates`/`difference_test`: is one
edge (or one node's centrality) really different from another, or is
that within bootstrap noise? `bootstrap_replicates` runs the same
nonparametric bootstrap `bootstrap_edge_stability` does, but keeps
every replicate's raw statistic vector instead of aggregating it, so
`difference_test` can build a paired percentile bootstrap CI for the
difference between any two of its entries. `threshold_by_inclusion_probability`
is a smaller, unrelated convenience: turn `EdgeStabilityResult
.inclusion_probability` into a "safe" adjacency matrix directly. See
`docs/decision_log.md`'s D-057.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Callable, Protocol, Sequence

import numpy as np
from scipy.stats import ConstantInputWarning, spearmanr


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


DEFAULT_PROPORTIONS_RETAINED: tuple[float, ...] = (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1)


def case_drop_resample(data: np.ndarray, n_keep: int, rng: np.random.Generator) -> np.ndarray:
    """Draw one subsample of `data` of `n_keep` rows, without replacement
    (unlike `bootstrap_resample`) -- the case-*dropping* bootstrap's own
    resampling scheme, not the nonparametric one."""
    n = data.shape[0]
    if not (0 < n_keep <= n):
        raise ValueError("n_keep must be between 1 and the number of rows in data")
    indices = rng.choice(n, size=n_keep, replace=False)
    return data[indices]


@dataclass(frozen=True)
class CaseDropResult:
    """Case-dropping bootstrap output for one dataset, one fit method,
    and one statistic.

    `full_sample_statistic` is `statistic(fit(data))` on the complete,
    undropped sample -- the reference every subsample is compared
    against. `replicate_statistics[p]` is a `(successful, n_features)`
    array: `statistic(...)`'s own output for every successful replicate
    at retained-proportion `p` (rows may vary in count across `p`
    levels since some replicates can fail). `successful`/`failed` are
    keyed the same way as `replicate_statistics`.
    """

    full_sample_statistic: np.ndarray
    replicate_statistics: dict[float, np.ndarray]
    successful: dict[float, int]
    failed: dict[float, int]


def case_drop_bootstrap(
    data: np.ndarray,
    fit: Callable[[np.ndarray], _FitResult],
    statistic: Callable[[_FitResult], np.ndarray],
    *,
    proportions_retained: Sequence[float] = DEFAULT_PROPORTIONS_RETAINED,
    bootstraps_per_proportion: int,
    rng: np.random.Generator,
) -> CaseDropResult:
    """At each retained-proportion `p` in `proportions_retained`, draw
    `bootstraps_per_proportion` subsamples of `round(p * n_rows)` rows
    (without replacement), run each through `fit`, and record
    `statistic(fit_result)` -- typically a centrality measure
    (`gopcnet.strength`, etc.) or the edge weights themselves. Feed the
    result to `cs_coefficient` to get a single correlation-stability
    coefficient out of it.

    A replicate on which `fit` raises `ValueError` is excluded, the
    same convention `bootstrap_edge_stability` uses. `proportions_retained`
    values must be in `(0, 1]`; each is independent, not compared to
    the others until `cs_coefficient` does so.
    """
    if not proportions_retained:
        raise ValueError("proportions_retained must not be empty")
    if any(not (0.0 < p <= 1.0) for p in proportions_retained):
        raise ValueError("every entry in proportions_retained must be in (0, 1]")
    if bootstraps_per_proportion < 1:
        raise ValueError("bootstraps_per_proportion must be at least 1")

    n = data.shape[0]
    full_sample_statistic = np.asarray(statistic(fit(data)))

    replicate_statistics: dict[float, np.ndarray] = {}
    successful: dict[float, int] = {}
    failed: dict[float, int] = {}

    for p in proportions_retained:
        n_keep = max(1, round(p * n))
        values: list[np.ndarray] = []
        n_failed = 0
        for _ in range(bootstraps_per_proportion):
            subsample = case_drop_resample(data, n_keep, rng)
            try:
                result = fit(subsample)
                values.append(np.asarray(statistic(result)))
            except ValueError:
                n_failed += 1
                continue
        replicate_statistics[p] = np.array(values) if values else np.empty((0, full_sample_statistic.shape[0]))
        successful[p] = len(values)
        failed[p] = n_failed

    return CaseDropResult(
        full_sample_statistic=full_sample_statistic,
        replicate_statistics=replicate_statistics,
        successful=successful,
        failed=failed,
    )


@dataclass(frozen=True)
class CSCoefficientResult:
    """Correlation-stability (CS) coefficient (Epskamp, Borsboom, &
    Fried, 2018) computed from a `CaseDropResult`.

    `cs_coefficient` is the largest case-drop proportion `d` (fraction
    of the original sample removed) such that, at `d` and at every
    smaller drop proportion, at least `pass_rate_threshold` of
    replicates correlate with the full-sample statistic at
    `correlation_threshold` or higher -- `0.0` if even the smallest
    tested drop proportion fails this. The literature's convention is
    to treat `0.25` as a bare-minimum and `0.5` as a comfortable
    threshold for interpreting the statistic at all.

    `pass_rate_by_proportion_retained` reports the raw per-level pass
    rate (not just the final coefficient) so a caller can see exactly
    where stability breaks down, not just the single summary number.
    A `NaN` correlation (a replicate whose statistic vector has zero
    variance) counts as not meeting the threshold, not as excluded.
    """

    cs_coefficient: float
    pass_rate_by_proportion_retained: dict[float, float]
    correlation_threshold: float
    pass_rate_threshold: float


def cs_coefficient(
    result: CaseDropResult,
    *,
    correlation_threshold: float = 0.7,
    pass_rate_threshold: float = 0.95,
) -> CSCoefficientResult:
    """Compute the CS-coefficient from a `case_drop_bootstrap` result.

    Correlation is Spearman's rho between each replicate's statistic
    vector and `result.full_sample_statistic` -- rank-based, since a
    centrality ordering, not a linear match, is usually what's being
    asked about. This is a convention, not the only reasonable choice;
    see `docs/decision_log.md`'s D-056.
    """
    if not (0.0 < correlation_threshold <= 1.0):
        raise ValueError("correlation_threshold must be in (0, 1]")
    if not (0.0 < pass_rate_threshold <= 1.0):
        raise ValueError("pass_rate_threshold must be in (0, 1]")

    pass_rate_by_proportion: dict[float, float] = {}
    for p, replicates in result.replicate_statistics.items():
        if replicates.shape[0] == 0:
            pass_rate_by_proportion[p] = 0.0
            continue
        meets_threshold = 0
        for row in replicates:
            # A replicate's statistic vector can be constant (e.g. every
            # node pruned to the same degree) -- correlation is genuinely
            # undefined there, not a bug; NaN is handled below, not
            # something to be warned about on every occurrence.
            with warnings.catch_warnings(), np.errstate(invalid="ignore"):
                warnings.simplefilter("ignore", ConstantInputWarning)
                correlation, _p_value = spearmanr(row, result.full_sample_statistic)
            if np.isfinite(correlation) and correlation >= correlation_threshold:
                meets_threshold += 1
        pass_rate_by_proportion[p] = meets_threshold / replicates.shape[0]

    # Proportions retained, from least dropped (highest p) to most dropped (lowest p).
    ordered_proportions = sorted(pass_rate_by_proportion, reverse=True)
    coefficient = 0.0
    for p in ordered_proportions:
        if pass_rate_by_proportion[p] < pass_rate_threshold:
            break
        coefficient = 1.0 - p

    return CSCoefficientResult(
        cs_coefficient=coefficient,
        pass_rate_by_proportion_retained=pass_rate_by_proportion,
        correlation_threshold=correlation_threshold,
        pass_rate_threshold=pass_rate_threshold,
    )


@dataclass(frozen=True)
class BootstrapReplicates:
    """Raw per-replicate statistic vectors from a nonparametric
    bootstrap (`bootstrap_resample` -- with replacement, full sample
    size), for `difference_test` or your own analysis. Unlike
    `EdgeStabilityResult`, nothing here is aggregated: memory cost is
    `O(bootstraps * n_features)`, not `O(n_features)`.

    `full_sample_statistic` is `statistic(fit(data))` on the complete
    sample -- the point-estimate reference `difference_test` reports
    the difference against. `replicate_statistics` is a
    `(successful, n_features)` array.
    """

    full_sample_statistic: np.ndarray
    replicate_statistics: np.ndarray
    successful: int
    failed: int


def bootstrap_replicates(
    data: np.ndarray,
    fit: Callable[[np.ndarray], _FitResult],
    statistic: Callable[[_FitResult], np.ndarray],
    *,
    bootstraps: int,
    rng: np.random.Generator,
) -> BootstrapReplicates:
    """Nonparametric bootstrap, recording every successful replicate's
    `statistic(fit(resample))` rather than aggregating it -- feed the
    result to `difference_test` to compare two of its entries (two
    edges' weights, or two nodes' centrality), or use the raw array
    directly for anything else a percentile bootstrap CI is useful for.

    A resample on which `fit` raises `ValueError` is excluded, the same
    convention `bootstrap_edge_stability` and `case_drop_bootstrap` use.
    """
    if bootstraps < 1:
        raise ValueError("bootstraps must be at least 1")
    full_sample_statistic = np.asarray(statistic(fit(data)))
    values: list[np.ndarray] = []
    failed = 0
    for _ in range(bootstraps):
        resample = bootstrap_resample(data, rng)
        try:
            result = fit(resample)
            values.append(np.asarray(statistic(result)))
        except ValueError:
            failed += 1
            continue
    if not values:
        raise RuntimeError("every bootstrap resample was degenerate; cannot compute replicate statistics")
    return BootstrapReplicates(
        full_sample_statistic=full_sample_statistic,
        replicate_statistics=np.array(values),
        successful=len(values),
        failed=failed,
    )


@dataclass(frozen=True)
class DifferenceTestResult:
    """Bootstrap difference test between two entries of the same
    statistic vector (two edges' weights, or two nodes' centrality).

    `difference` is the full-sample point estimate
    (`full_sample_statistic[index_a] - full_sample_statistic[index_b]`).
    `ci_low`/`ci_high` is the `alpha`-level percentile bootstrap CI of
    the *replicate* differences -- computed per replicate, from the
    same resampled data both entries were estimated from, so
    correlated variability between the two is preserved rather than
    treating them as independent. `significant` is True iff that CI
    excludes zero.
    """

    difference: float
    ci_low: float
    ci_high: float
    significant: bool
    alpha: float


def difference_test(
    replicates: BootstrapReplicates,
    index_a: int,
    index_b: int,
    *,
    alpha: float = 0.05,
) -> DifferenceTestResult:
    """Test whether entry `index_a` and entry `index_b` of `replicates`'
    statistic vector differ, using a paired percentile bootstrap CI on
    their difference. See `docs/decision_log.md`'s D-057 for why paired
    percentile rather than, say, a normal-approximation CI from
    `bootstrap_edge_stability`'s mean/std."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    n_features = replicates.full_sample_statistic.shape[0]
    if not (0 <= index_a < n_features) or not (0 <= index_b < n_features):
        raise ValueError("index_a and index_b must be valid indices into the statistic vector")
    if index_a == index_b:
        raise ValueError("index_a and index_b must refer to different entries")

    difference = float(replicates.full_sample_statistic[index_a] - replicates.full_sample_statistic[index_b])
    replicate_differences = (
        replicates.replicate_statistics[:, index_a] - replicates.replicate_statistics[:, index_b]
    )
    ci_low, ci_high = np.percentile(replicate_differences, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    significant = bool(ci_low > 0.0 or ci_high < 0.0)

    return DifferenceTestResult(
        difference=difference,
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        significant=significant,
        alpha=alpha,
    )


def threshold_by_inclusion_probability(
    inclusion_probability: np.ndarray,
    *,
    threshold: float = 0.5,
) -> np.ndarray:
    """A "safe" adjacency matrix built from bootstrap evidence rather
    than a single point estimate: an edge survives only if its
    `EdgeStabilityResult.inclusion_probability` is at least `threshold`.
    Matches the idea behind `bootnet`'s own `bootInclude()`."""
    if not (0.0 <= threshold <= 1.0):
        raise ValueError("threshold must be in [0, 1]")
    values = np.asarray(inclusion_probability, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("inclusion_probability must be a square matrix")
    adjacency = values >= threshold
    np.fill_diagonal(adjacency, False)
    return adjacency
