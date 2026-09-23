"""One PC-stable skeleton search over a correlation matrix, shared by
the PC comparator and GOPC's adjacency engine.

D-065's Q4 found that GOPC's growing-order pruning, at matched alpha, is
effectively PC's own skeleton search restricted to the screened candidate
graph. So one core serves both:

- **PC:** complete start graph, level 0 upward, unbounded
  (`pc_stable_skeleton(corr, n, alpha)`).
- **GOPC, adjacency engine:** the screened graph as the start, level 1
  upward, capped at `max_conditioning_size`. Level 0 is skipped because
  every screened-in pair already rejected a marginal test at
  `screening_alpha <= dpi_alpha`, so a level-0 test at `dpi_alpha` could
  not remove it.

The search follows PC-stable (Colombo & Maathuis, 2014) exactly as
`gopcnet.comparators.pc_skeleton.fit_pc_skeleton` does:

- neighbor sets are frozen at the start of each level
- both endpoints' neighbor sets are searched
- an edge is removed as soon as any tested set fails to reject
  independence
- a numerically singular conditioning set is inconclusive, not evidence
  of independence

The frozen `fit_pc_skeleton` is unchanged. Equivalence is pinned by
`tests/unit/test_skeleton_core.py`.

Tests run on a correlation matrix through
`gopcnet.dpi.correlation_based`, so any correlation estimate can be
searched, not only Pearson.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from gopcnet.dpi.correlation_based import partial_correlation_test_from_corr


@dataclass(frozen=True)
class SkeletonResult:
    """Outcome of a PC-stable skeleton search.

    All `(p, p)` arrays are symmetric.

    - `adjacency`: the retained edges.
    - `max_p_value`: for a retained edge, the largest p-value over every
      set tested for it (all `<= alpha`); for a removed edge, the p-value
      of the test that removed it; `NaN` for a pair never tested.
    - `min_abs_partial`: the signed partial correlation with the smallest
      magnitude among tests with a conditioning set of size `>= 1`
      (D-055's growing-order weight convention); `NaN` if there were
      none.
    - `separating_set`: for each removed edge `(i, j)` with `i < j`, the
      set that removed it.
    - `n_tests`: the number of tests actually run per pair.
    - `level_reached`: the last conditioning-set size the search entered.
      Unlike `PCSkeletonResult.max_conditioning_set_size`, this is not
      the last level at which something was removed.
    - `cap_reached`: a retained edge whose endpoints still had more
      candidate conditioning variables than `max_level`, so larger sets
      existed and were never tested. Always `False` when `max_level` is
      `None`.
    """

    adjacency: np.ndarray
    max_p_value: np.ndarray
    min_abs_partial: np.ndarray
    separating_set: dict[tuple[int, int], tuple[int, ...]]
    n_tests: np.ndarray
    level_reached: int
    cap_reached: np.ndarray


def _validate(corr: np.ndarray, n: int, alpha: float) -> np.ndarray:
    matrix = np.asarray(corr, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("corr must be a square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("corr must contain only finite values")
    if not np.allclose(matrix, matrix.T, rtol=0.0, atol=1e-10):
        raise ValueError("corr must be symmetric")
    if int(n) != n or n < 4:
        raise ValueError("n must be an integer of at least 4")
    if not (0.0 < float(alpha) < 1.0):
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    return matrix


def pc_stable_skeleton(
    corr: np.ndarray,
    n: int,
    alpha: float,
    *,
    start_adjacency: np.ndarray | None = None,
    start_level: int = 0,
    max_level: int | None = None,
    se_scale: float = 1.0,
) -> SkeletonResult:
    """PC-stable skeleton search on a correlation matrix.

    Parameters
    ----------
    corr : np.ndarray
        ``(p, p)`` correlation matrix. The diagonal is not read; only
        off-diagonal entries enter the tests.
    n : int
        Sample size behind `corr`, used for the Fisher-z degrees of
        freedom.
    alpha : float
        Significance level of every conditional-independence test.
    start_adjacency : np.ndarray, optional
        Boolean ``(p, p)`` starting graph. `None` means the complete
        graph (canonical PC). Edges absent here are never added.
    start_level : int, default 0
        First conditioning-set size tested.
    max_level : int, optional
        Last conditioning-set size tested. `None` means unbounded:
        continue until no pair has enough neighbors to test at the
        current level.
    se_scale : float, default 1.0
        Passed to `partial_correlation_test_from_corr`.
    """
    matrix = _validate(corr, n, alpha)
    p = matrix.shape[0]
    if start_level < 0 or (max_level is not None and max_level < 0):
        raise ValueError("start_level and max_level must be non-negative")

    if start_adjacency is None:
        adjacency = np.ones((p, p), dtype=bool)
    else:
        adjacency = np.asarray(start_adjacency, dtype=bool).copy()
        if adjacency.shape != (p, p) or not np.array_equal(adjacency, adjacency.T):
            raise ValueError("start_adjacency must be a symmetric (p, p) boolean matrix")
    np.fill_diagonal(adjacency, False)

    max_p_value = np.full((p, p), np.nan)
    min_abs_partial = np.full((p, p), np.nan)
    n_tests = np.zeros((p, p), dtype=int)
    separating_set: dict[tuple[int, int], tuple[int, ...]] = {}

    level = start_level
    level_reached = start_level
    while max_level is None or level <= max_level:
        level_reached = level
        neighbors = {a: set(np.flatnonzero(adjacency[a]).tolist()) for a in range(p)}
        any_testable = False
        removals: list[tuple[int, int, tuple[int, ...]]] = []
        for i in range(p):
            for j in range(i + 1, p):
                if not adjacency[i, j]:
                    continue
                tested: set[tuple[int, ...]] = set()
                removed = False
                for a, b in ((i, j), (j, i)):
                    candidates = neighbors[a] - {b}
                    if len(candidates) < level:
                        continue
                    any_testable = True
                    for subset in combinations(sorted(candidates), level):
                        if subset in tested:
                            continue  # the same set via the other endpoint: already decided
                        tested.add(subset)
                        try:
                            evidence = partial_correlation_test_from_corr(
                                matrix, n, i, j, subset, se_scale=se_scale
                            )
                        except ValueError:
                            continue  # inconclusive, as in the frozen primitive
                        n_tests[i, j] += 1
                        previous = max_p_value[i, j]
                        if np.isnan(previous) or evidence.p_value > previous:
                            max_p_value[i, j] = evidence.p_value
                        if level >= 1:
                            current = min_abs_partial[i, j]
                            if np.isnan(current) or abs(evidence.partial_correlation) < abs(current):
                                min_abs_partial[i, j] = evidence.partial_correlation
                        if evidence.p_value > alpha:
                            removals.append((i, j, subset))
                            removed = True
                            break
                    if removed:
                        break
        for i, j, subset in removals:
            adjacency[i, j] = adjacency[j, i] = False
            separating_set[(i, j)] = subset  # its p-value (> alpha) is already the running max
        if not any_testable:
            break
        level += 1

    cap_reached = np.zeros((p, p), dtype=bool)
    if max_level is not None:
        for i in range(p):
            for j in range(i + 1, p):
                if not adjacency[i, j]:
                    continue
                pool = max(np.count_nonzero(adjacency[i]) - 1, np.count_nonzero(adjacency[j]) - 1)
                cap_reached[i, j] = pool > max_level

    upper = np.triu_indices(p, k=1)
    for array in (max_p_value, min_abs_partial, n_tests, cap_reached):
        array[(upper[1], upper[0])] = array[upper]

    return SkeletonResult(
        adjacency=adjacency,
        max_p_value=max_p_value,
        min_abs_partial=min_abs_partial,
        separating_set=separating_set,
        n_tests=n_tests,
        level_reached=level_reached,
        cap_reached=cap_reached,
    )
