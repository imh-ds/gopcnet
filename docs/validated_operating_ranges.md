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
| DPI edge pruning — binary retain/prune decision (conditional-independence via partial correlation, three-node chain/fork/triangle motifs) | **Comfortable margin from `N >= 750`** (alpha decreasing `~0.15` at `750` to `~0.07` at `3000`, margin >= `.03`, see per-`N` table below). **Thin margin at `N = 700`** (alpha `(0.14, 0.16)`, margin `.012`, close to the `~.01` noise floor at 1000 replicates — a real pass, not a comfortable one) | `N <= 600`: no development-eligible alpha pair at all — decisive, not a tuning problem. `N = 650`: near-miss (eligible in development, fails validation). `N <= 300` (from the wider R2h sweep): decisive, structural gap across the whole tested alpha range | Stage 1g/1h/1i, `docs/decision_log.md` D-008, D-009, D-010 |
| `1 - p_value` as a candidate confidence-style score (continuous, non-binary) | Informative (Brier score well below a flat `0.25` baseline) across the *entire* tested range, `N = 100`-`3000` — **not** a validated calibration claim: no reliability diagram or prevalence-adjusted baseline has been computed, only a pooled Brier score against a flat baseline | Not yet chartered as a formal mechanism with its own gate — currently exploratory tracking only, alongside every Stage 1 charter since R2b, never itself validated as a decision rule or as calibrated | D-003 through D-009 (exploratory sections); no dedicated charter yet |

## Per-N alpha table for DPI pruning (from Stage 1h/1i)

| N | status | alpha pair | margin |
|---|---|---|---|
| 500 | REASSESS | none | — |
| 550 | REASSESS | none | — |
| 600 | REASSESS | none | — |
| 650 | REASSESS (near-miss) | (0.14, 0.16), failed validation | .018 (dev only) |
| 700 | PROCEED (thin) | (0.14, 0.16) | .012 |
| 750 | PROCEED | (0.14, 0.16) | .032 |
| 1000 | PROCEED | (0.12, 0.14) | .041 |
| 1500 | PROCEED | (0.10, 0.12) | .075 |
| 2000 | PROCEED | (0.08, 0.10) | .087 |
| 3000 | PROCEED | (0.06, 0.08) | .099 |

Not yet fit to a formula; see D-009's consequences for the proposed
follow-up.

## Recommended default floor: N = 750, not N = 700

Both `700` and `750` PROCEED, but they should not be treated as
interchangeable. **`N = 750` is the recommended default floor for
autonomous use; `N = 700` is documented as an available thin-margin
option, not a default.**

Justification:

1. **Margin size relative to noise.** `700`'s margin (`.012`) sits at
   roughly `1.3` standard errors above the pass/fail line at 1000
   validation replicates (`~.0095`-`.0126`, D-006/D-009). `750`'s margin
   (`.032`) sits at roughly `3`-`4` standard errors. A floor meant for
   *autonomous* use — the whole point of a "reliable without researcher
   oversight" threshold — needs to hold up under the ordinary sampling
   variation of a real dataset, not just the specific replicate draw that
   happened to pass in this simulation. `700`'s margin is the kind that
   has, in this exact project, previously flipped sides on independent
   re-checks (D-005, D-007). `750`'s has not.
2. **`650` is a near-miss right next door.** The evidence chain from
   `650` (fails) to `700` (barely passes) to `750` (comfortably passes)
   is a fast transition over a short interval, not a flat plateau. Being
   one step past a demonstrated failure case, at a margin close to the
   size of the step itself, is a fragile place to set a default.
3. **The floor's job is to be trustworthy without inspection.** Per this
   document's own stated stance (top of this file), the value of an
   "autonomous use" floor is that a researcher doesn't have to
   double-check it case by case. A thin-margin floor partially defeats
   that purpose — it would still warrant the researcher-judgment caveat
   this document recommends for below-floor `N`, just less severely.

`N = 700` remains a legitimate, disclosed option for a user who
understands and accepts the thinner margin (e.g., a researcher who cannot
collect more data and wants the best validated option available, with the
explicit caveat that it is close to the noise floor). It is not withheld
— it is labeled honestly.

## Practical translation for smaller-`N` datasets

For DPI edge-pruning decisions below the recommended default (`N < 750`;
`N = 700` is a disclosed thin-margin exception, not part of "below the
floor"; firmly below `N <= 600`; decisively below `N <= 300`): do not let
the automatic significance test decide whether an edge is real. Use it as
one input among others —
alongside prior domain knowledge, theoretical justification, or
qualitative reasoning the researcher states and defends — and let the
`1 - p_value` score (which stays informative, though not itself
validated as calibrated, even at small `N`) flag which specific edges are
most uncertain and therefore most in need of that justification, rather
than using it to make the cut itself.

## Maintenance

Add a row (or update an existing one) whenever a new charter validates
(or invalidates) a component's autonomous-use range. Stage 2 and later
will each need their own entries once chartered.
