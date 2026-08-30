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
| Candidate-edge screening — per-pair Fisher-z on raw correlation, uncorrected or BH-corrected (`p=15` network, 9 true / 96 null pairs) | `N in [750, 1500]` (both tested points PROCEED). Uncorrected `alpha=.001` sufficient (recall ~1.0, FDR ~.01); BH correction available but not required for this DGP | Not tested below `N=750` or above `N=1500`; not tested at `p != 15`; validated only in isolation, not composed with DPI pruning | Stage 2, `docs/decision_log.md` D-013 |
| Candidate-edge screening at **`p=30`** — same mechanism, same 9 true signals, 426 null pairs (`~4.4x` worse true:null ratio than `p=15`) | `N in [750, 1500]` (both PROCEED). Uncorrected `alpha=.0001` selected (recall `.999`-`1.0`, FDR `.005`-`.007`) — a margin comparable to or better than `p=15`'s, once the candidate grid was extended below Stage 2's original lower bound. **Do not assume `alpha=.001` still suffices at this `p`** — it clears the gate (FDR `~.045`-`.049`) but is no longer the selected rule, and `alpha=.005`+ fails outright (FDR `.19`+, not a near-miss). BH `q=.05` also passes; **`q=.10` narrowly missed its own nominal level** (FDR `.11`-`.11`) — do not trust BH `q=.10` at this true:null ratio without further checking | Now also validated composed with DPI pruning (see the row below) at `p=30`; not tested at `p` values beyond `30`, nor different true-signal counts/true:null ratios. Corrects an initial "BH becomes more necessary as `p` grows" intuition: extending the uncorrected grid downward fully compensated here, for this specific true-signal count | Stage 2e, `docs/decision_log.md` D-023 |
| Composed pipeline at **`p=30`** — screening (`alpha=.0001`, D-023) then DPI (`alpha=f(N)`, D-012), on **two** candidate shapes: disjoint chain/fork/triangle (D-024) and chain/fork/hub (D-025) | `N in [750, 1500]` (both PROCEED, both shapes). Final false-edge rate `.0001`-`.0001` on both shapes, identical to screening-alone's own rate at both `N` (D-014's "DPI cannot rescue an isolated false positive" finding replicated twice at `p=30`); indirect TPR `.838`-`.891` (triangle shape) / `.839`-`.883` (hub shape); true-edge FPR `<=.006`; shape-validation rate `.98`-`.99` on both (slightly higher than `p=15`'s `~.96`) | Validated only for these two candidate shapes at `p=30`. **Do not extrapolate to the shared-node-overlap shape — see the REASSESS row directly below.** Bootstrap stability remains untested at `p=30` for any shape (Stage 3's line of work is `p=15`-only); not tested beyond `p=30` | Stage 2f/2g, `docs/decision_log.md` D-024, D-025 |
| Composed pipeline at **`p=30`**, **shared-node-overlap shape** — same mechanism, same D-023 screening threshold | **REASSESS at both `N=750` and `N=1500`.** Overlap indirect TPR `.6365` (`N=750`, decisive failure) and `.762` (`N=1500`, a near-miss, `.038` below the `.80` gate) — worse at both `N` than `p=15`'s D-018 result (`.569`/`.817`, PROCEED at `N=1500`). Chain/fork TPR and true-edge FPR behave normally at both `N`; the failure is specific to the overlap motif's weak (`~.135`) cross-branch signal meeting `p=30`'s stricter, signal-agnostic threshold | **`N=1500` is no longer sufficient for this shape at `p=30`** — a demonstrated result, not a hypothetical caveat. The true floor at `p=30` is unlocated (untested above `1500`); a floor-search charter, mirroring D-010/D-011's exercise for the general DPI floor, would be a natural, well-scoped follow-up. Do not assume this generalizes to other weak-signal shapes not yet tested, nor that Stage 2f/2g's clean `p=30` results generalize to this shape | Stage 2h, `docs/decision_log.md` D-026 |
| Composed pipeline — screening (`alpha=.001`) then generalized DPI (`mintnet.pipeline.compose`) within any validated clique shape (size 3, 4, or 5), using the D-012 `alpha(N)` formula (`p=15`) | `N in [750, 1500]` for triad-only (D-014) and triad+hub (D-016) networks — both PROCEED at both `N`. **For the triad+shared-node-overlap network, PROCEED only at `N=1500`; REASSESS at `N=750`** (D-018) — see the overlap-specific row below for why. Final false-edge rate exactly tracks screening's own rate in every test so far; true-edge FPR is `0`-`.005` throughout | **Validated for disjoint candidate components of size 3, 4, or 5 that are full cliques — but "validated clique size" alone does not guarantee PROCEED at every `N`: screening must also reliably produce that clean clique for the specific DGP's signal strength (D-018).** Non-clique shapes, cliques of size 6+, larger networks, and components sharing variables across *more than one pair* of motifs are explicitly untested | Stage 2b/2c/2d, `docs/decision_log.md` D-014, D-016, D-018 |
| Multi-variable conditioning — DPI conditioning on all other nodes in a candidate component, tested on a 4-node hub (1 hub, 3 children) | `N in [750, 1500]` (both PROCEED, comfortable margin `.05`-`.09`). The existing D-012 `alpha(N)` formula works unmodified — no new fit needed for two-variable conditioning. **Wired into the composed pipeline, PROCEED at both tested `N`** (D-016) | Validated only for the hub shape (one shared cause, independent children). Components formed by two motifs sharing a node, or larger structures, remain untested | Stage 1k, `docs/decision_log.md` D-015 |
| Multi-variable conditioning — same rule, tested on a genuinely different topology: two `balanced` triangles sharing one node (5 variables, 3-variable conditioning) | Mechanism validated at `N in [750, 1500]` (both PROCEED, margin `.06`-`.09`) *when handed a clean component directly*. **Wired into the composed pipeline: PROCEED only at `N=1500`, REASSESS at `N=750`** (D-018) — the mechanism itself is fine at `N=750` (D-017); the bottleneck is screening's power to detect this DGP's weak (`~.135`) cross-branch correlation, only `~66%` at `N=750` (vs. `~98%` at `N=1500`), so a clean candidate clique forms only `~29%` of the time at `N=750` vs. `~92%` at `N=1500` | **Do not trust this shape below `N=1500` in a full pipeline**, even though the DPI mechanism and the general `N>=750` floor would suggest otherwise — this is a screening-detection-power limitation specific to weak-signal shapes, not a DPI limitation. The hub shape (above) does not share this caveat; its signal is strong enough to detect reliably at `N=750` too | Stage 1L/2d, `docs/decision_log.md` D-017, D-018 |
| Bootstrap edge stability — row resampling (`B=500`) of the composed screen-then-prune pipeline, final-edge stability `pi_final` thresholded at a calibrated `pi_min` | `N in [750, 1500]` (both PROCEED), on **all three** composed-pipeline DGPs studied so far: disjoint chain/fork/triangle (D-014), chain/fork/hub (D-016), and shared-node overlap (D-018) — `p=15` each. Smallest candidate `pi_min=.70` eligible and selected at both `N` on **all three** DGPs; stability recall `1.0` (`.995` at one cell), stability FDR `0`-`.007`, no measurable regression vs. the point-estimate baseline | **This gate answers a narrower question than "is the network accurate": it separates stable from unstable edges, and says nothing about indirect-edge pruning correctness.** On the overlap DGP specifically, this gate PROCEEDs at `N=750` even though D-018 independently found REASSESS there for indirect-edge pruning — these are answers to different questions about the same DGP and must never be merged or treated as contradictory. Not validated for `B` values other than `500`, or for any DGP outside `p=15`/`N in [750, 1500]` | Stage 3/3c/3d, `docs/decision_log.md` D-019, D-021, D-022 |
| Bootstrap stability, **indirect-edge categories specifically** (descriptive, not gated by the row above) — how the edges D-018 found problematic behave under resampling | Wrongly-retained/still-present overlap-indirect edges show *intermediate* stability at both tested `N` (`N=750` mean `pi_final` `.505`, only `23%` would survive even a `pi_min=.70` filter; `N=1500` mean `.653`) — clearly separated from null (`~.02`) but well below true edges (`~1.0`) at every measurement across D-019 and D-022 | Not itself a gate or a fix — see the dedicated rescue-mechanism row below (Stage 3b) for the one validated way to act on this observation | Stage 3/3d, `docs/decision_log.md` D-019, D-022 |
| Bootstrap stability **filtering as a rescue mechanism** — post-hoc `pi_final < pi_min` edge removal, gated on the shared-node-overlap DGP itself (`p=15`, `~.135` cross-branch correlation) | `N in [750, 1500]` (both PROCEED). Smallest candidate `pi_min=.80` eligible and selected at both `N` — rescues `N=750`'s overlap indirect-edge TPR from a `.558`-`.633` baseline (below the `.80` gate, replicating D-018) to `.867` after filtering, with true-edge FPR exactly `0` throughout at every tested `pi_min` | Validated **only** for this exact DGP shape and signal strength, at `B=500`. **Not** validated: other under-powered shapes, other signal strengths, `pi_min` values below `.80` (untested whether an even cheaper threshold also works), or adopting this as a permanent stage in `mintnet.pipeline.compose` (a separate architecture decision; the `~500x` per-dataset bootstrap cost is unresolved for production use) | Stage 3b, `docs/decision_log.md` D-020 |

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

## Candidate alpha(N) formula (from Stage 1j, D-012)

```
alpha(N) = 0.5222 - 0.0566 * ln(N)
```

Fit on the six points above (`R^2 = .997`) and validated by predicting a
single alpha (no grid search) at four interpolated, held-out `N` values
never used in fitting — all four passed with comfortable margin (`.039`
to `.097`, all `>= .02`; see `docs/decision_log.md` D-012 and
`docs/stage1j_report.md`).

**Scope: interpolation only, `N` in `[700, 3000]`.** Do not extrapolate
below `700` (the D-010/D-011 floor) or above `3000` (edge of the tested
range) — both are outside this formula's validated scope, regardless of
what the formula computes there. This is a *candidate* default rule for a
future production implementation, not itself a production default; that
adoption decision is separate and has not been made.

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

## Caveat: weak-signal overlapping shapes need N = 1500, not the general N = 750 floor

The `N = 750` default above applies to the DPI mechanism itself and to
every candidate shape tested so far *except one*. **The shared-node-
overlap shape (two motifs meeting at one variable, D-017/D-018) requires
`N >= 1500` in a full pipeline, not `750`**, even though `750` clears
every other bar in this document (the general DPI floor, and the DPI
mechanism's own accuracy on this exact shape when handed a clean
component directly).

The reason is specific and does not generalize to other shapes: at
`N=750`, screening only detects this shape's weak (`~.135`) cross-branch
correlation `~66%` of the time per edge, so all four cross-branch edges
are simultaneously detected — the condition needed to form a clean,
DPI-eligible candidate clique — only `~29%` of the time. The other `71%`
of the time, DPI is correctly *not* applied (per the pipeline's
conservative design), and un-pruned candidate edges pass straight
through, dragging the overlap-specific indirect-edge accuracy down to
`.569`, below the `.80` gate. At `N=1500`, per-edge detection is `~98%`,
clean-clique formation is `~92%`, and the shape clears the gate
comfortably (`.817`).

**This caveat is shape-specific, not a general revision to the `N=750`
floor.** The hub shape (D-015/D-016) has a stronger signal and does not
share it — it clears the gate at `N=750` in the full pipeline just as
reliably as it does as an isolated mechanism test. Before trusting any
*new* multi-node candidate shape at the general `N=750` floor, check its
screening-detection power specifically, the way D-018 did — do not assume
it transfers from the hub case.

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
