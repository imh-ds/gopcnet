"""The package's two public GOPC entry points: `fit_gopc` (growing-order,
the recommended default) and `fit_gopc_fixed_order` (fixed-order, the
paper's other variant). Both take a data array and return an adjacency
matrix directly -- the same signature -- so switching between them is a
one-line change.

`fit_gopc` (growing-order) is the recommended default. See
docs/decision_log.md's D-053: growing-subset DPI closes most of GOPC's
precision gap with PC's skeleton (MATERIAL on `overlap`, PARTIAL on
`chain_fork_hub`, both composed shapes Stage 5g actually tested) with
zero measured recall cost anywhere. This supersedes
`compose_screen_then_prune` as the recommended entry point for new
work.

`fit_gopc_fixed_order` is a thin convenience wrapper around
`compose_screen_then_prune`, added for API parity with `fit_gopc` --
`compose_screen_then_prune` itself is deliberately left unmodified and
still directly exported -- it is the frozen mechanism
`docs/stage5a_charter.md` through `stage5f_charter.md` (D-047 through
D-052) and `docs/stage3_charter.md`'s bootstrap-stability tooling were
validated and archived against; changing it in place would silently
invalidate already-cited evidence rather than superseding it
transparently.
"""

from __future__ import annotations

import numpy as np

from gopcnet.pipeline.compose import compose_screen_then_prune
from gopcnet.pipeline.growing_subset_dpi import growing_subset_dpi
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def fit_gopc(
    data: np.ndarray, *, screening_alpha: float, dpi_alpha: float, max_conditioning_size: int = 4
) -> np.ndarray:
    """Estimate a network with growing-order GOPC (the paper's
    recommended default; see `docs/decision_log.md`'s D-053).

    Screens every pair by Fisher-z correlation, then prunes indirect
    edges with a conditional-independence test whose conditioning set
    grows -- one variable at a time, drawn from the rest of the
    candidate edge's own connected component -- up to
    `max_conditioning_size`, stopping as soon as any tested subset
    fails to reject independence. Closely related to the PC
    algorithm's own skeleton search, restricted to a pre-screened
    candidate graph rather than starting from a complete one -- see
    the paper's Section 3.2 for the full disclosure of that
    relationship.

    Parameters
    ----------
    data : np.ndarray
        ``(n_samples, n_variables)`` array of continuous, approximately
        Gaussian observations. Categorical or ordinal data is out of
        scope (not validated).
    screening_alpha : float
        Significance level for the initial pairwise correlation
        screen. A pair is a candidate edge only if its screening
        p-value is at or below this threshold.
    dpi_alpha : float
        Significance level for the conditional-independence pruning
        step. Independent of `screening_alpha`.
    max_conditioning_size : int, default 4
        Largest conditioning-set size tested before giving up and
        retaining an edge unconditionally cleared up to that point.
        `4` is this method's own validated default (Stage 6a) and has
        not been re-tuned for other values.

    Returns
    -------
    np.ndarray
        ``(n_variables, n_variables)`` boolean, symmetric adjacency
        matrix.

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    array([[False,  True, False],
           [ True, False,  True],
           [False,  True, False]])

    See Also
    --------
    fit_gopc_fixed_order : the paper's other GOPC variant, closer in
        spirit to LOPC (Zuo et al., 2014).
    """
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, screening_alpha)
    result = growing_subset_dpi(data, screened, dpi_alpha, max_conditioning_size=max_conditioning_size)
    return result.adjacency


def fit_gopc_fixed_order(data: np.ndarray, *, screening_alpha: float, dpi_alpha: float) -> np.ndarray:
    """Estimate a network with fixed-order GOPC (the paper's other
    variant; see `docs/decision_log.md`'s D-047 through D-052 and the
    paper's Section 3.1).

    Screens every pair by Fisher-z correlation, then, within each
    connected component of the resulting candidate-edge graph that
    forms a clique of a validated size (three, four, or five nodes),
    tests every pair once, conditioning on every other member of that
    same clique -- so the conditioning order is fixed by local clique
    size (one, two, or three variables) rather than escalating.
    Components that are not validated-size cliques are passed through
    without any conditional test; this is a disclosed scope boundary,
    not an oversight (see the paper's Section 3.1). Architecturally the
    closest of the two GOPC variants to LOPC (Zuo, Yu, Tadesse, &
    Ressom, 2014), though the two differ in their specific stopping
    rule -- see the paper's Section 2.3 for the precise comparison.

    This is a thin convenience wrapper around
    `gopcnet.pipeline.compose.compose_screen_then_prune`, which remains
    the frozen mechanism this package's own archived evidence
    (`docs/stage5a_charter.md` through `stage5f_charter.md`) was
    validated against -- this wrapper does not change its behavior,
    only its call signature (returning the adjacency matrix directly,
    matching `fit_gopc`'s own signature, rather than the
    ``(adjacency, shapes)`` tuple `compose_screen_then_prune` itself
    returns).

    Parameters
    ----------
    data : np.ndarray
        ``(n_samples, n_variables)`` array of continuous, approximately
        Gaussian observations. Categorical or ordinal data is out of
        scope (not validated).
    screening_alpha : float
        Significance level for the initial pairwise correlation
        screen.
    dpi_alpha : float
        Significance level for the conditional-independence pruning
        step.

    Returns
    -------
    np.ndarray
        ``(n_variables, n_variables)`` boolean, symmetric adjacency
        matrix.

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc_fixed_order
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> fit_gopc_fixed_order(data, screening_alpha=0.05, dpi_alpha=0.05)
    array([[False,  True, False],
           [ True, False,  True],
           [False,  True, False]])

    See Also
    --------
    fit_gopc : the paper's recommended default variant, which closes
        most of this variant's own precision gap with PC (D-053).
    """
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, screening_alpha)
    final, _shapes = compose_screen_then_prune(data, screened, dpi_alpha)
    return final
