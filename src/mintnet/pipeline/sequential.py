"""Sequential/greedy conditioning engine. See docs/stage4a_charter.md.

Builds the final adjacency matrix by ranking candidate pairs by marginal
association strength and testing each, strongest first, against
already-confirmed neighbors -- rather than requiring every pair in a
connected component to be simultaneously flagged before any conditioning
test runs (`mintnet.pipeline.compose_screen_then_prune`'s design). This
is a second, independently validated engine, not a replacement for the
conservative one: see
`outline/information_network_technical_build_plan_v3_2026-08-30.md`.
"""

from __future__ import annotations

import numpy as np

from mintnet.dpi.multi_conditional import compute_partial_correlation_evidence
from mintnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def sequential_screen_and_prune(data: np.ndarray, alpha: float) -> np.ndarray:
    """Rank-then-condition sequential pruning, using one alpha for both the
    initial marginal candidacy test and the conditional test, per
    docs/stage4a_charter.md's frozen mechanism.

    Pruning is permanent: once an edge is removed because some
    already-confirmed neighbor explains it away, it is never reconsidered
    against a different neighbor or re-tested later. This one-directional
    commitment is this engine's central, deliberately un-mitigated risk in
    this charter -- Stage 4c stress-tests it directly.
    """
    if not np.isscalar(alpha) or not (0.0 < float(alpha) < 1.0):
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    alpha_value = float(alpha)

    evidence = compute_pairwise_screening_evidence(data)
    flagged = screen_uncorrected(evidence, alpha_value)
    p = data.shape[1]

    candidates = [(i, j) for i in range(p) for j in range(i + 1, p) if flagged[i, j]]
    candidates.sort(key=lambda pair: abs(evidence.z_statistic[pair[0], pair[1]]), reverse=True)

    confirmed = np.zeros((p, p), dtype=bool)
    for i, j in candidates:
        shared = [k for k in range(p) if k != i and k != j and confirmed[i, k] and confirmed[j, k]]
        if not shared:
            confirmed[i, j] = confirmed[j, i] = True
            continue
        explained_away = any(
            compute_partial_correlation_evidence(data, i, j, [k]).p_value > alpha_value for k in shared
        )
        if not explained_away:
            confirmed[i, j] = confirmed[j, i] = True
    return confirmed
