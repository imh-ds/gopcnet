# Stage 5i Charter: PC Significance-Level Sweep — Is GOPC's Tradeoff Against PC an Alpha Artifact?

Status: **FROZEN before results**
Date: 2026-09-20

## Background and objective

D-051 (Stage 5e) and D-053 (Stage 5g) established a tradeoff between PC's
skeleton and growing-order GOPC on the same draws: PC has higher
precision on the composed `p=15` networks, and lower recall on the weak
true edges of `triangle_moderate`/`triangle_strong` (true partial
correlations `.12` and `.08`; `triangle_strong`, `N=1750`: PC `.923` vs.
GOPC-original `.986` vs. EBICglasso `.999`). The manuscript's practical
guidance (`manuscript/paper.qmd` Sections 6.1, 6.2, 7) rests on that
tradeoff — in particular on the claim that growing-order GOPC recovers
most of PC's precision "without PC's cost in recall on weak, asymmetric
edges."

**A confound this arc has never controlled.** The two methods were run at
very different significance levels, and the difference is large and
directional:

| | screening (marginal) test | conditional (pruning) test |
|---|---|---|
| PC (D-051) | `alpha = .01` | `alpha = .01` (same single value) |
| Growing-order GOPC (D-053) | `screening_alpha = .001` | `dpi_alpha = alpha(N)` = `.148`, `.131`, `.108`, `.100` at `N = 750, 1000, 1500, 1750` |

GOPC's conditional tests therefore run at a level **10–15x looser** than
PC's, while its marginal screen is **10x stricter**. Both effects are
predicted to move the observed metrics in exactly the directions D-051
reported: a looser conditional level retains more weak true edges
(higher recall) and more false ones (lower precision); a stricter marginal
screen removes noise pairs earlier. D-051's own correction acknowledged
this asymmetry for the *precision* side (GOPC's `alpha(N)` was calibrated
on these DGPs, PC's `.01` was not) but not for recall, where it cuts the
other way. `fit_gopc`'s own stopping rule ("stopping as soon as any tested
subset fails to reject independence") is PC's, so the two procedures
differ in *how they are parameterized* at least as much as in *what they
do*; whether the reported tradeoff survives equal treatment of the
significance level is an open empirical question, not something the
existing evidence can answer.

**Objective.** Determine whether the PC-vs-GOPC precision/recall tradeoff
in D-051/D-053 is a property of the algorithms or an artifact of their
default significance levels — and if it is not purely an artifact,
whether GOPC's specific design choice (strict marginal screen, loose
conditional prune, decoupled) reaches operating points a single-alpha PC
cannot.

**What this charter is not.** Not a re-litigation of D-051 or D-053, both
of which stand as reported for the configurations they tested. Not a new
method, DGP, or data type. Not a retuning of GOPC. Not a claim about
performance on networks unlike the ones tested.

## Design

**Shapes**: all five Stage 5a shapes (`chain_fork_hub`, `overlap`,
`triangle_balanced`, `triangle_moderate`, `triangle_strong`), `strength =
.5`, unchanged — full shape grid retained for row-level comparability
with D-047/D-051/D-053.

**Sample sizes**: `N = [750, 1000, 1500, 1750]`, the manuscript's validated
range (Section 4.3; `N < 700` is outside GOPC's calibrated `alpha(N)`).

**Data access — paired, not merely comparable.** Reuses
`stage5a._condition_seed` and `master_seed = 20260830` unchanged, with
`dgp_index` and `sample_index` derived from Stage 5a's **full 7-value `N`
grid** (`[400, 500, 600, 750, 1000, 1500, 1750]`), not from this charter's
four-value grid — the seed-derivation pitfall Stage 5h's charter names
explicitly. Every `(dgp, N, replicate)` cell therefore draws the *identical*
dataset D-047, D-051, and D-053 used. `2,000` replicates per cell.

**Methods, fit on identical data at every replicate:**

1. `pc@alpha` for `alpha in {.001, .005, .01, .025, .05, .10, .20}`
   (`fit_pc_skeleton`; `.01` is D-051's own value).
2. `pc@matched`: `alpha` set to GOPC's own `alpha(N)` for that cell
   (`.1476`, `.1313`, `.1084`, `.0996`), computed exactly as D-053 did.
3. `gopc_growing@validated`: `fit_gopc` with `screening_alpha = .001`,
   `dpi_alpha = alpha(N)`, `max_conditioning_size = 4` — D-053's
   configuration, unchanged. This is the reference GOPC point.
4. `gopc_matched@.01` and `gopc_matched@.10`: `fit_gopc` with `screening_alpha
   = dpi_alpha = alpha` and `max_conditioning_size = p - 2` (uncapped
   relative to the network), used only for the mechanism check below.
   If an uncapped fit is computationally infeasible at `p=15`, use the
   largest feasible cap, disclose it, and restrict the mechanism claim
   accordingly — an implementation-time decision, not an analysis choice.

5. `pc@1.25x.01` and `pc@1.25xmatched`: PC at `1.25 x` the `.01` and
   matched alphas (`.0125` and `1.25 x alpha(N)`), used only to set the
   Q4 noise floor (a trivially different PC setting).

EBICglasso is not re-run: this charter's question concerns PC and GOPC
only, and D-047's archived numbers remain the reference for it.

**Development/validation split**, per this project's own convention:
replicates `0`-`999` are *development*, `1000`-`1999` are *validation*.
Development replicates are used only to select a single `alpha` per `N`
(rule below). **Every reported comparison uses validation replicates
only.**

**Single-alpha selection rule (predeclared).** The three triangle shapes
have `p = 3` and every pair is a true edge, so precision is `1.0` for any
alpha and nothing penalizes a loose alpha; the two composed shapes (`p =
15`) are the only place false positives can occur. Equal weight per shape
would give the triangles three of five votes at zero false-positive cost
and bias `alpha*` loose. The rule therefore weights the two groups equally:
for each `N`, `alpha*(N)` is the value on the seven-point PC grid
(excluding `pc@matched`) maximizing `0.5 x (mean dev F1 over the 2 composed
shapes) + 0.5 x (mean dev F1 over the 3 triangle shapes)`, ties broken
toward the smaller `alpha`. This models the deployable case: a practitioner
cannot tune `alpha` per network. **Sensitivity analyses, reported alongside
and never substituted for the primary verdict:** (a) equal weight per
shape, (b) `alpha*` selected separately per group. Per-shape oracle `alpha`
(best dev F1 per shape) is reported as an upper bound on PC's tunability,
labeled as such, and **not** used in any verdict below.

**Fairness disclosure, stated up front.** GOPC's `alpha(N)`/`alpha(p)` were
calibrated truth-informed on these very DGPs (D-012, D-049); selecting
`alpha*` for PC on the development half of the same DGPs is the symmetric
treatment. Neither result says anything about performance on a network
unlike these five; that requires new DGPs (see Consequences).

## Sharding

Shard by `(dgp, N)` — `5 x 4 = 20` shards — using
`.github/workflows/sharded_benchmark.yml`'s existing two-dimension
support. Per-fit cost is `~0.01`-`0.07 s`; `13` methods x `2,000`
replicates is on the order of `25` minutes per shard.

## Decision structure

**Two hard gates (pipeline integrity only — not about any hypothesis):**

- **G1.** `pc@.01` reproduces the archived Stage 5e rows
  (`evidence/stage5_benchmarks/stage5e_pc_skeleton/raw_metrics.csv`) for
  every shared `(dgp, N, replicate)`: `(n_estimated_edges, precision,
  recall)` identical in **at least 99.9%** of replicate-level rows, and every
  cell-level mean within `.001`.
- **G2.** `gopc_growing@validated` reproduces the archived Stage 5g rows
  by the same criterion.

The 99.9% (rather than bitwise) criterion allows for a Fisher-z p-value
landing exactly on a threshold under a different platform's floating
point. **If either gate fails, stop and resolve before interpreting
anything else** — a failure means the pairing or the code has drifted, and
every downstream comparison would be uninterpretable.

**Descriptive questions (no PROCEED/REASSESS gate — same standing as every
prior R6 charter).** Each is answered on validation replicates, per `(shape,
N)`, with the project's own `.01` tolerance (Stage 5e). Cell-count verdicts
are counted **within each shape** (out of 4 sample sizes), never pooled
across shapes, so one shape cannot mask another. Every comparison also
reports the paired per-replicate difference (same draws) with a 95%
bootstrap confidence interval. Recall and precision are reported separately
and prominently, never only folded into F1.

**Predeclared predictions for Q1** (a test, not a formality). With `p = 3`,
the only conditioning set that can matter is `|S| = 1`, and a Fisher-z test
of a partial correlation `rho` at level `alpha` has power `Phi(z - c) +
Phi(-z - c)` with `z = arctanh(rho) x sqrt(N - |S| - 3)`, `c =
z_{1-alpha/2}`. Verified against `gopcnet.simulation.motifs`: the true
partial correlations are `.35/.25/.12` (`triangle_moderate`) and
`.45/.25/.08` (`triangle_strong`), so each triangle has two edges with
power `~1` at every `N >= 750` and one weak edge. Predicted recall is
`(2 + power)/3`:

| shape (weak `rho`) | `N` | PC `.01` | GOPC / `pc@matched` |
|---|---|---|---|
| `triangle_strong` (.08) | 750 | .783 | .924 |
| | 1000 | .827 | .949 |
| | 1500 | .900 | .978 |
| | 1750 | .927 | .985 |
| `triangle_moderate` (.12) | 750 | .921 | .989 |
| | 1000 | .964 | .996 |
| | 1500 | .994 | 1.000 |
| | 1750 | .998 | 1.000 |

Archived `triangle_strong`, `N = 1750`: PC `.921`/`.923` vs. GOPC `.984`/`.986`
(observed vs. predicted within `.006`). If the sweep's `pc@matched` recall
differs from these predictions by more than `.02` in a cell, the alpha-only
explanation is incomplete there and that cell is reported as such.

- **Q1 — Is the weak-edge recall deficit an alpha artifact?** On
  `triangle_moderate` and `triangle_strong` (`2 x 4 = 8` cells; precision
  is `1.0` for every method there, so recall is the only driver): does
  `pc@matched` reach within `.01` of `gopc_growing@validated` recall, or
  exceed it? *Per shape: 4 of 4 or 3 of 4 `N`: the deficit was the
  significance level for that shape, and the manuscript's recall claim
  must be restated. 0-1 of 4: the deficit survives alpha-matching for that
  shape. 2 of 4: mixed, reported per cell.* The `8`-cell headline is the
  conjunction of the two shapes, not a pooled count.
- **Q2 — Is PC's precision edge an alpha artifact?** On `chain_fork_hub`
  and `overlap` (8 cells): does `pc@matched` precision stay within `.01`
  of, or above, `gopc_growing@validated` precision? *Per shape: if
  PC's precision falls below GOPC's by more than `.01` at >= 3 of 4 `N`,
  PC's edge was the strictness of `alpha = .01`, and GOPC's decoupled
  strict-screen / loose-prune design reaches precision at loose alpha that
  single-alpha PC cannot. If PC holds within `.01` at >= 3 of 4, loosening
  alpha costs PC nothing and GOPC gains nothing on this axis. 2 of 4 either
  way is mixed and reported per cell.*
- **Q3 — Does one alpha suffice?** At `alpha*(N)`, on validation
  replicates, in how many of the `5 x 4 = 20` cells is PC comparable to or
  better than GOPC (F1 within `.01` or higher), and is there any `N` at
  which PC is comparable-or-better on **all five shapes at once**? Reported
  under the primary selection rule and both sensitivity rules. A
  single-alpha PC that matches GOPC everywhere means GOPC offers no
  operating point PC lacks; a shape/N pattern where it cannot is evidence
  of a genuinely different tradeoff.
- **Q4 — Mechanism check.** At `alpha in {.01, .10}`, per-replicate
  agreement between `gopc_matched@alpha` and `pc@alpha` (exact-adjacency
  match rate; mean symmetric-difference edge count), per shape. GOPC draws
  conditioning candidates from a screened component while PC-stable uses
  current adjacency sets, so exact equality is **not** expected, and no
  threshold here gates anything. The interpretation
  is anchored to a **data-derived noise floor** rather than fixed bands:
  the same two statistics computed between `pc@alpha` and `pc@1.25 x alpha`
  (a trivially different PC), per shape. Predeclared: if `gopc_matched`-vs-
  `pc` disagreement is no larger than the noise floor plus `.5` edge
  (mean symmetric-difference count) in a shape, the procedures are
  "effectively the same search at matched alpha there, and the observed
  difference between the methods is parameterization"; if larger, they are
  "materially different even at matched alpha" for that shape, and the
  manuscript's "close to PC's own search" language needs revisiting.
  Exact-match rate is reported but not used for the verdict, since at
  `p = 15` one flipped edge breaks it.

**Required reporting whatever the outcome**: the full grid of
precision/recall/F1 for every method x `(dgp, N)` cell — none omitted; a
recall-vs-alpha and precision-vs-alpha figure per shape with GOPC's
validated point overlaid; the per-shape oracle-`alpha` table (labeled as
an upper bound); the Q4 agreement table; and G1/G2 stated explicitly as
their own section.

## Explicit non-goals

- **No retuning of GOPC** (`alpha(N)`, `alpha(p)`, `screening_alpha`,
  `max_conditioning_size` all as D-053 left them).
- **No new DGPs, no non-Gaussian or ordinal data, no strength sweep** — the
  signal-strength axis is Stage 5h's; the messy-data axis is a separate
  charter.
- **No oracle-tuned PC presented as a deployable method.** The per-shape
  oracle `alpha` is an upper bound only.
- **No adaptive extension of the `alpha` grid** after seeing results; the
  grid above is final at freeze.
- **No modification of any archived evidence**
  (`evidence/stage5_benchmarks/stage5e_pc_skeleton/`, `stage5g_growing_subset/`).
- **No claim of GOPC or PC superiority in general.** As in every prior R6
  charter, the verdicts are descriptive and scoped to these five shapes,
  these `N`, Gaussian data.

## Required evidence

Resolved configuration; this charter's SHA-256 (recorded at freeze);
commit and runtime metadata; raw per-replicate metrics for all `13`
methods at every `(dgp, N)` cell (`5 x 4 x 13 x 2,000` rows, no cell
omitted); a report presenting G1/G2, Q1-Q4, and the required figures and
tables above. Archived under
`evidence/stage5_benchmarks/stage5i_pc_alpha_sweep/`.

## Consequences

Each outcome has a predeclared consequence for the manuscript, so the
result cannot be selectively read afterward:

- **Q1 shows the recall deficit is an alpha artifact:** Sections 5.2, 6.1,
  6.2 and 7 of `paper.qmd` must drop or restate "without PC's cost in
  recall on weak, asymmetric edges" as a statement about PC *at its
  conventional `alpha = .01`*, and the "practical guidance" recommendation
  that rests on it must be rewritten.
- **Q2 shows PC's precision edge is an alpha artifact and Q1 shows the
  recall deficit persists (or vice versa):** the corresponding half of the
  tradeoff stands and is reported with the mechanism (alpha decoupling)
  named.
- **Q3 shows a single-alpha PC matches GOPC everywhere, and Q4 shows the
  procedures are effectively identical at matched alpha:** the honest
  positioning becomes that growing-order GOPC is PC with a different
  default alpha structure. The paper's remaining contribution is the
  EBICglasso comparison and the psychometrics application (already its
  stated scope, Section 1), and `gopcnet` should give `fit_pc_skeleton`
  equal standing, including edge weights.
- **Q2 and Q3 show a distinct, reproducible operating point PC's single
  alpha cannot reach:** this strengthens the paper's claim and supplies
  the mechanism it currently lacks.

In every case, a decision-log entry (next number after D-064) records the
result; `docs/validated_operating_ranges.md` gets an addendum; and the
manuscript claims above are updated in the same change that records the
result, not deferred. The two axes this charter deliberately does not
touch — weak edges inside a *composed* `p=15` network (where recall is
`1.0` for every method today and so cannot separate them) and
non-Gaussian/ordinal data — remain the next two charters, in that order.

## Resolutions of the pre-freeze questions

1. **Alpha grid:** kept as is (`.001` to `.20` plus `matched`); the wide
   grid traces the whole recall/precision curve and brackets conventional
   choices. A Bonferroni-scale PC configuration is deferred, not added.
2. **Tolerance and cutoffs:** `.01` kept; cutoffs now per shape (>= 3 of 4
   `N`), plus paired-difference confidence intervals.
3. **Q4 bands:** replaced by a data-derived PC-vs-PC noise floor.
4. **`triangle_balanced`:** kept. Its three edges all have partial
   correlation `.25` (well powered at every tested `N`), so it is a negative
   control: no separation between methods is expected at any `alpha >= .005`,
   and a difference there would flag a pipeline problem rather than a finding.
5. **`alpha*` rule:** changed from equal-weight-per-shape to a 50/50
   composed/triangle weighting, with pooled and per-group selection as
   sensitivity analyses (reason given under the selection rule).

Known scope limit, disclosed: all `N >= 750`; applied psychology studies
are often smaller, where alpha matters more (D-051: PC recall `.72` at
`N = 400`). Small-`N` behavior is outside GOPC's calibrated range and is
not addressed here.
