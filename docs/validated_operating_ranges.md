# Validated Operating Ranges

This is a maintained reference, not a chronological log (see
`docs/decision_log.md` for the narrative). It tracks, per methodological
component, the sample size below which the component's automatic
data-driven decision should not be trusted on its own.

## How to read this table

The project's working stance (set 2026-08-29, informing how this table is
used going forward): at large `N`, the data carries enough power to drive
decisions with minimal researcher input — closer to exploratory analysis.
At small `N`, a component may still produce a number, but that number
should not be trusted to decide anything autonomously; the researcher's
own theoretical or conceptual justification should carry the actual
decision, with the data used to check consistency rather than to drive the
call. The **minimum N for autonomous use** column marks that transition
per component, as currently evidenced. Below it, treat the component's
output as informative context for a researcher-justified decision, not as
the decision itself.

This table records what has been *validated*, not what is *assumed*. A
component not listed here has no validated range yet; a range listed here
is only as good as the evidence behind it, cited in the Source column.

## Table

| Component | Reliable (autonomous) from | Below this | Source |
|---|---|---|---|
| Bivariate association estimation (KSG-1 mutual information, `k=20`, continuous Gaussian) | `N >= 100` (validated `100`-`1000`; gate specifically checked at `N=300, 500`) | Not separately tested below `N=100`; no evidence of a lower-bound problem in the tested range | Stage 0, `docs/decision_log.md` D-001 |
| DPI edge pruning — binary retain/prune decision (conditional-independence via partial correlation, three-node chain/fork/triangle motifs) | `N >= 750`, with alpha decreasing from `~0.15` at `750` to `~0.07` at `3000` (see per-`N` table below) | `N <= 300`: decisive, structural gap — no alpha value makes the binary decision reliable, not a tuning problem. `N = 500`: boundary case, gap of only one grid step in the tested alpha resolution — plausibly closeable with finer resolution, but thin-margin even so; treat as unreliable for autonomous use until (and unless) separately validated | Stage 1g/1h, `docs/decision_log.md` D-008, D-009 |
| DPI edge confidence score (`1 - p_value`, continuous, non-binary) | Informative (well-calibrated, Brier score well below the naive `0.25` baseline) across the *entire* tested range, `N = 100`-`3000` | Not yet chartered as a formal mechanism with its own gate — currently exploratory evidence only, tracked alongside every Stage 1 charter since R2b but never itself validated as a decision rule | D-003 through D-009 (exploratory sections); no dedicated charter yet |

## Per-N alpha table for DPI pruning (from Stage 1h, `N >= 750`)

| N | alpha pair | margin |
|---|---|---|
| 750 | (0.14, 0.16) | .032 |
| 1000 | (0.12, 0.14) | .041 |
| 1500 | (0.10, 0.12) | .075 |
| 2000 | (0.08, 0.10) | .087 |
| 3000 | (0.06, 0.08) | .099 |

Not yet fit to a formula; see D-009's consequences for the proposed
follow-up.

## Practical translation for smaller-`N` datasets

For DPI edge-pruning decisions below the validated floor (`N < 750`,
firmly below `N <= 300`): do not let the automatic significance test
decide whether an edge is real. Use it as one input among others —
alongside prior domain knowledge, theoretical justification, or
qualitative reasoning the researcher states and defends — and let the
confidence score (which stays informative even at small `N`) flag which
specific edges are most uncertain and therefore most in need of that
justification, rather than using it to make the cut itself.

## Maintenance

Add a row (or update an existing one) whenever a new charter validates
(or invalidates) a component's autonomous-use range. Stage 2 and later
will each need their own entries once chartered.
