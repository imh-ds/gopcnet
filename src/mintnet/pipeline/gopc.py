"""The recommended default GOPC pipeline. See docs/decision_log.md's
D-053: growing-subset DPI closes most of GOPC's precision gap with PC's
skeleton (MATERIAL on `overlap`, PARTIAL on `chain_fork_hub`, both
composed shapes Stage 5g actually tested) with zero measured recall
cost anywhere. This supersedes `compose_screen_then_prune` as the
recommended entry point for new work.

`compose_screen_then_prune` itself is deliberately left unmodified and
still exported -- it is the frozen mechanism `docs/stage5a_charter.md`
through `stage5f_charter.md` (D-047 through D-052) and
`docs/stage3_charter.md`'s bootstrap-stability tooling were validated
and archived against; changing it in place would silently invalidate
already-cited evidence rather than superseding it transparently.
"""

from __future__ import annotations

import numpy as np

from mintnet.pipeline.growing_subset_dpi import growing_subset_dpi
from mintnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def fit_gopc(
    data: np.ndarray, *, screening_alpha: float, dpi_alpha: float, max_conditioning_size: int = 4
) -> np.ndarray:
    """Screen by Fisher-z correlation, then prune via growing-subset
    DPI. `max_conditioning_size=4` is D-053's own validated default
    (Stage 6a, ported from mintnet's mi-native branch), not re-tuned
    here."""
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, screening_alpha)
    result = growing_subset_dpi(data, screened, dpi_alpha, max_conditioning_size=max_conditioning_size)
    return result.adjacency
