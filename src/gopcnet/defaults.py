"""Default significance levels for `fit_gopc` and `fit_gopc_fixed_order`.

GOPC's contribution, as restated in `docs/decision_log.md`'s D-065, is
that one fixed default holds up across network regimes that PC needs
per-dataset alpha tuning to handle. This module is that default, made
callable: when a user omits `screening_alpha` or `dpi_alpha`,
`resolve_alphas` fills it in from the rules below, which are exactly
the settings the archived Stage 5 evidence was produced with. See the
defaults-API entry in `docs/decision_log.md` (D-068) for the full
convention.

- **Pruning** (`dpi_alpha`): D-012's fitted `alpha(N) = a + b * ln(N)`
  (`linear_log_n`), with `a` and `b` copied at full precision from
  `gopcnet.experiments.stage1j_fit` (a test pins them). Validated by
  interpolation for `N` in `[700, 3000]`; `N >= 750` is the
  recommended floor (D-011).
- **Screening** (`screening_alpha`): `.001` for `p <= 15` (the value
  D-047 validated at both `p = 3` and `p = 15`), and above that D-049's
  log-linear interpolation between Stage 2's anchors `(15, .001)` and
  `(30, .0001)`. The raw interpolation *rises* below `p = 15` (to about
  `.21` at `p = 3`, never validated), hence the clamp. Validated for
  `p` in `[3, 30]`: `p = 3, 15` in D-047, the interpolation up to
  `p = 27` in Stage 5c (D-049), and `p = 30` is Stage 2's own
  calibrated anchor.

Outside those ranges a default is still returned -- a researcher with
`N = 300` needs *some* setting -- but an
`OutsideValidatedRangeWarning` says the value is extrapolated. These
defaults are the current best evidence, not a final answer: they were
calibrated on the same motif family the benchmarks use, and are
scheduled for replacement by rules validated on held-out network
families (`docs/development_plan/phase2_small_sample.md`, Stage 7c).
"""

from __future__ import annotations

import math
import numbers
import warnings
from dataclasses import dataclass

# D-012's selected `linear_log_n` form, full precision (see module docstring).
_DPI_INTERCEPT = 0.5222288254774476
_DPI_LOG_SLOPE = -0.05659085931817262
_DPI_MIN_ALPHA = 1e-4  # the fitted line crosses zero near N = 10,200

# D-049's two Stage 2 anchor points for the p-adjusted screening alpha.
_SCREEN_P_LOW, _SCREEN_ALPHA_LOW = 15.0, 0.001
_SCREEN_P_HIGH, _SCREEN_ALPHA_HIGH = 30.0, 0.0001

DPI_VALIDATED_N: tuple[int, int] = (700, 3000)  # D-012
DPI_RECOMMENDED_MIN_N: int = 750  # D-011
SCREENING_VALIDATED_P: tuple[int, int] = (3, 30)  # D-047 (p = 3, 15), D-049 (to 27), Stage 2 anchor (30)


class OutsideValidatedRangeWarning(UserWarning):
    """A default significance level was used outside the range it was
    validated on. The value is still usable, but it is an extrapolation,
    not a validated setting -- see `docs/validated_operating_ranges.md`."""


def _dpi_alpha_and_notes(n: int) -> tuple[float, list[str]]:
    if int(n) != n or n < 4:
        raise ValueError("n must be an integer of at least 4")
    notes: list[str] = []
    alpha = _DPI_INTERCEPT + _DPI_LOG_SLOPE * math.log(n)
    low, high = DPI_VALIDATED_N
    if n < low or n > high:
        notes.append(
            f"dpi_alpha default at N = {n} is extrapolated: D-012's alpha(N) formula is validated "
            f"only for N in [{low}, {high}] (recommended floor N >= {DPI_RECOMMENDED_MIN_N}, D-011). "
            "See docs/validated_operating_ranges.md, 'Practical translation for smaller-N datasets'."
        )
    elif n < DPI_RECOMMENDED_MIN_N:
        notes.append(
            f"N = {n} is inside alpha(N)'s validated range but below the recommended floor "
            f"N >= {DPI_RECOMMENDED_MIN_N} (D-011: N = 700 passed validation with a thin margin)."
        )
    if alpha <= _DPI_MIN_ALPHA:
        alpha = _DPI_MIN_ALPHA
        notes.append(f"alpha(N) is non-positive at N = {n}; clipped to {_DPI_MIN_ALPHA}.")
    return alpha, notes


def _screening_alpha_and_notes(p: int) -> tuple[float, list[str]]:
    if int(p) != p or p < 2:
        raise ValueError("p must be an integer of at least 2")
    notes: list[str] = []
    if p <= _SCREEN_P_LOW:
        alpha = _SCREEN_ALPHA_LOW
    else:
        slope = (math.log10(_SCREEN_ALPHA_HIGH) - math.log10(_SCREEN_ALPHA_LOW)) / (
            math.log(_SCREEN_P_HIGH) - math.log(_SCREEN_P_LOW)
        )
        alpha = float(10.0 ** (math.log10(_SCREEN_ALPHA_LOW) + slope * (math.log(p) - math.log(_SCREEN_P_LOW))))
    low, high = SCREENING_VALIDATED_P
    if p < low or p > high:
        notes.append(
            f"screening_alpha default at p = {p} is outside its validated range p in [{low}, {high}] "
            "(D-047, D-049); the value is an extrapolation."
        )
    return alpha, notes


def _warn(notes: list[str], stacklevel: int) -> None:
    for note in notes:
        warnings.warn(note, OutsideValidatedRangeWarning, stacklevel=stacklevel + 1)


def default_dpi_alpha(n: int) -> float:
    """The default pruning significance level at sample size `n`:
    D-012's `alpha(N) = a + b * ln(N)`.

    Warns (`OutsideValidatedRangeWarning`) outside `N` in `[700, 3000]`
    and for `700 <= N < 750` (D-011's thin-margin band); never raises
    for small `n` (except `n < 4`, where no Fisher-z test exists).

    Examples
    --------
    >>> round(default_dpi_alpha(1000), 4)
    0.1313
    """
    alpha, notes = _dpi_alpha_and_notes(n)
    _warn(notes, stacklevel=2)
    return alpha


def default_screening_alpha(p: int) -> float:
    """The default marginal-screening significance level for `p`
    variables: `.001` for `p <= 15`, D-049's log-linear interpolation
    above. Warns outside `p` in `[3, 30]`.

    Examples
    --------
    >>> default_screening_alpha(15)
    0.001
    """
    alpha, notes = _screening_alpha_and_notes(p)
    _warn(notes, stacklevel=2)
    return alpha


@dataclass(frozen=True)
class ResolvedAlphas:
    """The significance levels a fit actually used, and where each came from."""

    screening_alpha: float
    dpi_alpha: float
    screening_source: str  # "user" or "default"
    dpi_source: str  # "user" or "default"
    warnings: tuple[str, ...]


def _validate_user_alpha(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not (0.0 < float(value) < 1.0):
        raise ValueError(f"{name} must satisfy 0 < {name} < 1")
    return float(value)


def resolve_alphas(
    n: int,
    p: int,
    screening_alpha: float | None = None,
    dpi_alpha: float | None = None,
    *,
    stacklevel: int = 2,
) -> ResolvedAlphas:
    """Fill in whichever of `screening_alpha` / `dpi_alpha` is `None`
    from the defaults, validate user-supplied values, and emit an
    `OutsideValidatedRangeWarning` for each default used outside its
    validated range. A user-supplied value is never second-guessed
    against a validated range -- it is the user's explicit choice.

    Also warns (`UserWarning`) if `screening_alpha > dpi_alpha`: the
    design assumes the marginal screen is the stricter of the two tests
    (Section 3.0 of the paper). Not an error -- Stage 5i's matched-alpha
    configurations set them equal on purpose.

    `stacklevel` has the same meaning as in `warnings.warn`: the
    default attributes warnings to `resolve_alphas`'s caller; wrappers
    (such as `fit_gopc`) pass a larger value so warnings point at user
    code.
    """
    notes: list[str] = []
    if screening_alpha is None:
        screening_value, screening_notes = _screening_alpha_and_notes(p)
        notes.extend(screening_notes)
        screening_source = "default"
    else:
        screening_value = _validate_user_alpha("screening_alpha", screening_alpha)
        screening_source = "user"
    if dpi_alpha is None:
        dpi_value, dpi_notes = _dpi_alpha_and_notes(n)
        notes.extend(dpi_notes)
        dpi_source = "default"
    else:
        dpi_value = _validate_user_alpha("dpi_alpha", dpi_alpha)
        dpi_source = "user"
    _warn(notes, stacklevel=stacklevel)
    if screening_value > dpi_value:
        warnings.warn(
            f"screening_alpha ({screening_value:g}) is larger than dpi_alpha ({dpi_value:g}); "
            "GOPC's design assumes the marginal screen is the stricter test.",
            UserWarning,
            stacklevel=stacklevel,
        )
    return ResolvedAlphas(
        screening_alpha=screening_value,
        dpi_alpha=dpi_value,
        screening_source=screening_source,
        dpi_source=dpi_source,
        warnings=tuple(notes),
    )
