"""The package's two public GOPC entry points: `fit_gopc` (growing-order,
the recommended default) and `fit_gopc_fixed_order` (fixed-order, the
paper's other variant). Both take a data array and return a
`GOPCResult` -- the same signature -- so switching between them is a
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

from dataclasses import dataclass
from typing import Literal

import numpy as np

from gopcnet.defaults import ResolvedAlphas, resolve_alphas
from gopcnet.pipeline.compose import compose_screen_then_prune
from gopcnet.pipeline.growing_subset_dpi import growing_subset_dpi
from gopcnet.pipeline.skeleton_core import pc_stable_skeleton
from gopcnet.pipeline.weights import compute_fixed_order_weights, compute_growing_order_weights
from gopcnet.screening import ScreeningEvidence, compute_pairwise_screening_evidence, screen_uncorrected


@dataclass(frozen=True)
class GOPCResult:
    """A fitted GOPC network: which edges survive, and how strong each one is.

    `weights` is a signed, symmetric, zero-diagonal partial-correlation
    matrix, zero everywhere `adjacency` is False. See
    `gopcnet.pipeline.weights` and `docs/decision_log.md`'s D-055 for
    exactly what partial correlation each retained edge's weight is
    (it differs by variant, and by whether the edge was ever
    conditioning-tested at all).

    `screening_alpha` and `dpi_alpha` record the significance levels the
    fit actually used -- whether passed explicitly or filled in from
    `gopcnet.defaults` -- so a fitted result can be reported
    reproducibly. They default to `None` only so that a `GOPCResult`
    built directly from an adjacency and weights (outside `fit_gopc`)
    stays valid.
    """

    adjacency: np.ndarray
    weights: np.ndarray
    screening_alpha: float | None = None
    dpi_alpha: float | None = None
    diagnostics: GOPCDiagnostics | None = None


@dataclass(frozen=True)
class GOPCDiagnostics:
    """Per-pair evidence from `fit_gopc(..., engine="adjacency")`.

    Not produced by the frozen component engine. See
    `gopcnet.pipeline.skeleton_core.SkeletonResult` for the exact meaning
    of each array.

    - `screened`: the candidate graph after marginal screening.
    - `max_p_value`: for a retained edge, the largest p-value over every
      conditioning set tested for it.
    - `n_tests`: the number of conditional tests run per pair.
    - `cap_reached`: a retained edge for which larger conditioning sets
      existed beyond `max_conditioning_size` but were never tested.
    - `separating_set`: for each pruned edge `(i, j)` with `i < j`, the
      set that removed it.
    """

    screened: np.ndarray
    max_p_value: np.ndarray
    n_tests: np.ndarray
    cap_reached: np.ndarray
    separating_set: dict[tuple[int, int], tuple[int, ...]]


def fit_gopc(
    data: np.ndarray,
    *,
    screening_alpha: float | None = None,
    dpi_alpha: float | None = None,
    max_conditioning_size: int = 4,
    engine: Literal["component", "adjacency"] = "component",
) -> GOPCResult:
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
    screening_alpha : float, optional
        Significance level for the initial pairwise correlation
        screen. A pair is a candidate edge only if its screening
        p-value is at or below this threshold. Omit it to use
        `gopcnet.defaults.default_screening_alpha(p)`.
    dpi_alpha : float, optional
        Significance level for the conditional-independence pruning
        step. Independent of `screening_alpha`. Omit it to use
        `gopcnet.defaults.default_dpi_alpha(N)`.
    max_conditioning_size : int, default 4
        Largest conditioning-set size tested before giving up and
        retaining an edge unconditionally cleared up to that point.
        `4` is this method's own validated default (Stage 6a) and has
        not been re-tuned for other values.
    engine : {"component", "adjacency"}, default "component"
        Which conditioning sets the pruning step searches.

        - `"component"` is the frozen, validated mechanism
          (`growing_subset_dpi`) that every archived result used. It
          draws sets from the edge's whole connected component in the
          screened graph, fixed after screening. When screening passes
          most pairs, as in densely inter-correlated item sets, the
          number of tests grows combinatorially with `p`.
        - `"adjacency"` runs the PC-stable search
          (`gopcnet.pipeline.skeleton_core`) on the screened graph. It
          draws sets from each endpoint's *current* neighbors, which
          shrink as edges are pruned. That is far fewer tests, and it is
          sufficient under PC's own assumptions. It also fills
          `GOPCResult.diagnostics`.

        The default stays `"component"` until a charter has validated
        the adjacency engine against it
        (`docs/development_plan/phase1_external_validity.md`,
        Stage 7a). The adjacency engine's weights follow the same D-055
        convention.

    Defaults and validated range
    ----------------------------
    Called as `fit_gopc(data)`, both significance levels come from
    `gopcnet.defaults`: the settings every archived Stage 5 benchmark
    used (D-012's `alpha(N)` for pruning; `.001` for screening at
    `p <= 15`, D-049's `p`-adjusted value above). They are validated
    for `N` in `[700, 3000]` (recommended `N >= 750`) and `p` in
    `[3, 30]`, Gaussian data only. Outside that range the fit still
    runs but emits a `gopcnet.defaults.OutsideValidatedRangeWarning`.
    The values used are recorded on the result. Explicitly passed
    values are used exactly as given.

    Returns
    -------
    GOPCResult
        `.adjacency`: ``(n_variables, n_variables)`` boolean, symmetric
        adjacency matrix. `.weights`: same shape, signed partial
        correlations (zero where `.adjacency` is False) -- see
        `docs/decision_log.md`'s D-055 for exactly what each retained
        edge's weight represents for this variant.
        `.screening_alpha`, `.dpi_alpha`: the significance levels used.

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05).adjacency
    array([[False,  True, False],
           [ True, False,  True],
           [False,  True, False]])

    With the defaults (`N = 500` is below the validated range, so an
    `OutsideValidatedRangeWarning` explains that the pruning level is
    extrapolated):

    >>> import warnings
    >>> with warnings.catch_warnings():
    ...     warnings.simplefilter("ignore")
    ...     result = fit_gopc(data)
    >>> result.screening_alpha, round(result.dpi_alpha, 4)
    (0.001, 0.1705)

    See Also
    --------
    fit_gopc_fixed_order : the paper's other GOPC variant, closer in
        spirit to LOPC (Zuo et al., 2014).
    """
    if engine not in ("component", "adjacency"):
        raise ValueError('engine must be "component" or "adjacency"')
    if int(max_conditioning_size) != max_conditioning_size or max_conditioning_size < 0:
        raise ValueError("max_conditioning_size must be a non-negative integer")
    alphas = _resolve_for(data, screening_alpha, dpi_alpha)
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, alphas.screening_alpha)
    if engine == "adjacency":
        return _fit_adjacency_engine(np.asarray(data), evidence, screened, alphas, max_conditioning_size)
    result = growing_subset_dpi(data, screened, alphas.dpi_alpha, max_conditioning_size=max_conditioning_size)
    weights = compute_growing_order_weights(
        data,
        result.adjacency,
        screened,
        result.conditioning_size_used,
        max_conditioning_size=max_conditioning_size,
    )
    return GOPCResult(
        adjacency=result.adjacency,
        weights=weights,
        screening_alpha=alphas.screening_alpha,
        dpi_alpha=alphas.dpi_alpha,
    )


def fit_gopc_fixed_order(
    data: np.ndarray, *, screening_alpha: float | None = None, dpi_alpha: float | None = None
) -> GOPCResult:
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
    only its call signature (returning a `GOPCResult`, matching
    `fit_gopc`'s own signature, rather than the ``(adjacency, shapes)``
    tuple `compose_screen_then_prune` itself returns).

    Parameters
    ----------
    data : np.ndarray
        ``(n_samples, n_variables)`` array of continuous, approximately
        Gaussian observations. Categorical or ordinal data is out of
        scope (not validated).
    screening_alpha : float, optional
        Significance level for the initial pairwise correlation
        screen. Omit it to use the same default as `fit_gopc`.
    dpi_alpha : float, optional
        Significance level for the conditional-independence pruning
        step. Omit it to use the same default as `fit_gopc` (see its
        "Defaults and validated range" section).

    Returns
    -------
    GOPCResult
        `.adjacency`: ``(n_variables, n_variables)`` boolean, symmetric
        adjacency matrix. `.weights`: same shape, signed partial
        correlations (zero where `.adjacency` is False) -- see
        `docs/decision_log.md`'s D-055 for exactly what each retained
        edge's weight represents for this variant.

    Examples
    --------
    >>> import numpy as np
    >>> from gopcnet import fit_gopc_fixed_order
    >>> rng = np.random.default_rng(0)
    >>> x1 = rng.normal(size=500)
    >>> x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    >>> data = np.column_stack([x1, x2, x3])
    >>> fit_gopc_fixed_order(data, screening_alpha=0.05, dpi_alpha=0.05).adjacency
    array([[False,  True, False],
           [ True, False,  True],
           [False,  True, False]])

    See Also
    --------
    fit_gopc : the paper's recommended default variant, which closes
        most of this variant's own precision gap with PC (D-053).
    """
    alphas = _resolve_for(data, screening_alpha, dpi_alpha)
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, alphas.screening_alpha)
    final, shapes = compose_screen_then_prune(data, screened, alphas.dpi_alpha)
    weights = compute_fixed_order_weights(data, final, shapes)
    return GOPCResult(
        adjacency=final,
        weights=weights,
        screening_alpha=alphas.screening_alpha,
        dpi_alpha=alphas.dpi_alpha,
    )


def _fit_adjacency_engine(
    data: np.ndarray,
    evidence: ScreeningEvidence,
    screened: np.ndarray,
    alphas: ResolvedAlphas,
    max_conditioning_size: int,
) -> GOPCResult:
    corr = evidence.correlation.copy()  # zero diagonal from screening; the tests need the unit diagonal
    np.fill_diagonal(corr, 1.0)
    # start_level=1: every screened-in pair already rejected a marginal test at
    # screening_alpha <= dpi_alpha, so a level-0 test at dpi_alpha could not prune it.
    core = pc_stable_skeleton(
        corr,
        data.shape[0],
        alphas.dpi_alpha,
        start_adjacency=screened,
        start_level=1,
        max_level=max_conditioning_size,
    )
    # D-055: minimum-magnitude partial correlation over tested sets of size >= 1;
    # an edge never conditioning-tested keeps its marginal correlation.
    weights = np.where(np.isnan(core.min_abs_partial), evidence.correlation, core.min_abs_partial)
    weights = np.where(core.adjacency, weights, 0.0)
    np.fill_diagonal(weights, 0.0)
    return GOPCResult(
        adjacency=core.adjacency,
        weights=weights,
        screening_alpha=alphas.screening_alpha,
        dpi_alpha=alphas.dpi_alpha,
        diagnostics=GOPCDiagnostics(
            screened=screened,
            max_p_value=core.max_p_value,
            n_tests=core.n_tests,
            cap_reached=core.cap_reached,
            separating_set=core.separating_set,
        ),
    )


def _resolve_for(data: np.ndarray, screening_alpha: float | None, dpi_alpha: float | None) -> ResolvedAlphas:
    shape = np.shape(data)
    if len(shape) != 2:
        raise ValueError("data must be a two-dimensional array")
    # stacklevel 4: resolve_alphas -> _resolve_for -> fit_gopc* -> user code
    return resolve_alphas(shape[0], shape[1], screening_alpha, dpi_alpha, stacklevel=4)
