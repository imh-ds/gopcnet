# Stage 6a Charter: Edge-Evidence Tiers and Cross-Community Bridge Inference — Validation Charter

Status: **FROZEN before results.** Written up
from ad hoc scratch validation (unfrozen, uncommitted exploratory scripts,
`evidence_tiers_prototype.py`, `evidence_tiers_validation.py`,
`evidence_tiers_validation2.py`, session scratchpad only) that motivated
this charter but is **not** itself evidence — everything here must be
re-run under this charter's own frozen configuration before any claim is
made in the package or the manuscript. Resolutions of the five pre-freeze
questions are recorded in the final section.
Date: 2026-09-22

## Background and objective

Every estimator this package validates (`fit_gopc`, `fit_gopc_fixed_order`,
`fit_pc_skeleton`, `fit_ebicglasso`) outputs a single yes/no adjacency per
edge. D-065 (Stage 5i) additionally established that GOPC's screen-then-
prune design is, by construction, PC's own search restricted to a
pre-screened candidate set (Q4). Conversation with the user identified two
related opportunities that do not require a new estimator:

1. **Edge-evidence tiers.** For a pair that survives the initial marginal
   screen, its behavior across many conditioning-set sizes (not just
   whether it is eventually pruned) carries information: a link that
   vanishes under *every* tested set is different from one that vanishes
   only under one specific set (which names a candidate mediator) or only
   under large sets (diffuse shared variance). A single keep/prune bit
   discards this.
2. **Cross-community bridge inference.** D-063 already computes bridge
   *centrality* for a caller-supplied community assignment, but only for
   edges the estimator already kept. Weak or cross-construct links are
   exactly the edges most likely to be pruned first by any conditional-
   independence method, so a bridging question ("is symptom cluster A
   connected to cluster B, and through what?") is currently answered only
   by the final adjacency, with no visibility into near-miss edges.

**Preliminary scratch evidence (not frozen, motivating only).** A hand-
built test — two 3-node clusters, one true weak cross-cluster edge, and one
"confound decoy" pair with **no direct edge** whose marginal correlation
exists only because both endpoints separately depend on a third, common
variable — showed that ranking candidate cross-cluster pairs by raw
marginal correlation picks the *decoy* over the *true* bridge in 87-100%
of replicates when the confound is even moderately strong, while ranking
by the fraction of conditioning sets under which a pair's partial
correlation stays significant ("survival fraction") correctly identifies
the true bridge in 70-99% of replicates depending on its strength, with a
1-3% false-confirmation rate on the decoy. This held up under wider
shapes (four-node clusters, two simultaneous bridges, a true negative
control with no bridge at all). **One result is a genuine, expected
limitation rather than a defect to fix:** when the confounding variable is
present in the true data-generating process but *not observed* (dropped
before the method ever sees the data), the false-confirmation rate on the
decoy does **not** shrink with sample size (roughly 14-15% at every `N`
from 500 to 3000, against roughly 1-2% and shrinking when the same
confound is observed). This is expected of any conditional-independence
method — an unmeasured common cause cannot be conditioned on — and must be
documented as a headline, permanent limitation, not something this
charter's validation can pass or fail on fixing.

**Objective.** Determine whether an edge-evidence-tier and bridge-ranking
layer, added on top of an existing estimator's fitted candidate set,
reliably distinguishes true weak/bridging edges from spurious
associations (including confounded ones where the confound is measured),
under a frozen, predeclared configuration and DGP registry — and to
document, with a quantified and predeclared check, the case (unmeasured
confounding) where it cannot.

**What this charter is not.** Not a new structure-learning estimator —
this is a reporting/inference layer over an existing fitted candidate
graph (reusing `fit_gopc`'s own screening step; see Design). Not a claim
of causal discovery. Not a fix for unmeasured confounding — Design
includes a predeclared check that this limitation persists as expected,
not a target to eliminate. Not a retuning of any frozen estimator.

## Design

### New DGP registry (`gopcnet.simulation.bridges`, to be added)

A general precision-matrix builder from an edge list (`(i, j, rho)`
triples plus a within-cluster clique helper), positive-definiteness
checked at import time exactly as `gopcnet.simulation.motifs` already
does for its own fixtures. Five frozen shapes, all Gaussian:

1. **`confound_trap_observed`**: clusters `A = {0,1,2}`, `B = {3,4,5}`,
   within-cluster partial correlations `0.30`; one true bridge `(0,3)` at
   `rho_bridge`; a confound node `Z = 6` linked to `2` and `5` at
   `rho_confound`, **included** in the data given to the method. Candidate
   pairs: all 9 cross-cluster pairs `A x B`.
2. **`confound_trap_latent`**: identical data-generating process to (1),
   but `Z` is **dropped** before the method sees the data — the
   unmeasured-confound stress test.
3. **`no_bridge_negative_control`**: identical to (1) but with **no**
   `(0,3)` edge at all — pure false-confirmation-rate baseline.
4. **`larger_clusters`**: 4-node cliques (`p=9` including the confound) —
   tests whether a bigger conditioning-candidate pool degrades detection
   (the "many chances to fail" concern raised earlier in this project's
   own discussion of PC's dense-network behavior). **Implementation-time
   amendment (before any run was dispatched):** a 4-node clique at
   `RHO_WITHIN = 0.30` is not positive definite across this charter's full
   `(rho_bridge, rho_confound)` grid (checked directly; `rho_confound =
   0.40` alone drives the minimum eigenvalue negative). `larger_clusters`
   therefore uses a reduced within-cluster strength, `RHO_WITHIN_LARGE_
   CLUSTER = 0.25`, verified positive definite with margin (minimum
   eigenvalue `>= .09`) at every grid point; every other shape keeps
   `RHO_WITHIN = 0.30` unchanged. This is a feasibility fix, not an
   analysis choice, and Q4's comparison against the 3-node-cluster shapes
   is read with this disclosed difference in mind.
5. **`double_bridge`**: two true bridges (`(0,3)`, `(1,4)`) plus one
   confound decoy (`(2,5)` via `Z=6`) — tests whether both are recovered
   at once, a stricter joint criterion than single-bridge recovery.

**Bridge strength grid**: `rho_bridge in {0.05, 0.08, 0.12, 0.18}`
(weak-edge range, consistent with `triangle_moderate`/`triangle_strong`'s
own `0.08`/`0.12` true partial correlations). **Confound strength grid**:
`rho_confound in {0.20, 0.30, 0.40}` — `0.20` added to bracket the
boundary at which the "trap" (decoy marginal correlation exceeding the
true bridge's) turns on: an exact-marginal-correlation check at the
frozen `rho_within = 0.30` found the crossing sits between `rho_confound
= 0.20` and `0.25` for the weakest bridge (`0.05`) and never occurs at
all for the two strongest bridges (`0.12`, `0.18`) within this grid. So
`0.20` gives a genuine "no-trap" contrast cell (marginal-correlation
ranking is expected to work about as well as the survival-fraction score
there) alongside `0.30`/`0.40`'s "trap active" cells — a control this
charter's own preliminary scratch validation did not have, since it never
tested `rho_confound` below `0.30`.

**Sample sizes**: `N in {500, 750, 1000, 1500, 3000}` — `500` is *below*
GOPC's own validated `alpha(N)` floor (`docs/validated_operating_ranges.md`,
`N >= 700`) and is included **deliberately and only** to characterize
behavior outside the validated range, reported separately and never used
to pass or fail any gate.

**Seeding**: a new, disjoint stage tag, following this project's
`_condition_seed`-style convention (`SeedSequence([master_seed, stage_tag,
shape_index, rho_bridge_index, rho_confound_index, sample_index,
replicate])`). `master_seed = 20260830` unchanged. Development/validation
split as every prior charter: replicates `0`-`999` development, `1000`-
`1999` validation. Replicate count: `2,000` per cell (development +
validation combined), matching every prior R6 charter — reducible for a
smoke config exactly as Stage 5i's `configs/stage5i_smoke.yaml` does.

### Method under test

Built as an additive function, not a new estimator: given a fitted
candidate graph from `fit_gopc`'s own screening step
(`compute_pairwise_screening_evidence` + `screen_uncorrected`, unchanged),
for every screened-in pair, compute partial correlations over **every**
conditioning-set size `0` through `max_conditioning_size` (default `4`,
matching `fit_gopc`'s own validated default) drawn from the pair's
candidate-neighbor pool, using the existing
`gopcnet.dpi.multi_conditional.compute_partial_correlation_evidence`
primitive (no new statistical test). Records, per pair: the survival
fraction (share of tested sets whose p-value is at or below the pruning
alpha), the maximum p-value seen (a `pMax`-style diagnostic, already
implicit in PC's own literature), and the conditioning set responsible
for the largest p-value (the "explainer").

**Baselines compared, same draws, same candidate pool:**
- Raw marginal `|correlation|` ranking (the naive approach this charter
  argues against).
- The survival-fraction score (this charter's candidate addition).
- The `pMax`-style score (an existing PC diagnostic, not a novel
  statistic — included so any claim of novelty is scoped correctly, per
  this project's own standing discipline of checking prior art before
  claiming a contribution).
- Bootstrap-confirmed rate: row-resample the data `B=200` times, refit,
  and report the fraction of resamples in which a pair is classified
  "confirmed" (survival fraction `== 1.0`).

## Metrics and predeclared thresholds

Per `(shape, rho_bridge, rho_confound, N)` cell, on validation replicates
only:

- **Top-k recovery rate (primary, per-bridge).** For every true bridge
  individually, the fraction of replicates in which it ranks within the
  top `n_bridges + 1` scoring pairs (i.e., top `2` for single-bridge
  shapes, top `3` for `double_bridge`'s two bridges) under each ranking
  rule — one slack slot so a strong decoy crowding out one bridge is not
  scored as a total failure of the *other*, independently-detectable
  bridge. Reported per bridge, not pooled, so `double_bridge`'s two
  bridges (which need not be equally strong from replicate to replicate)
  are each visible.
- **Exact joint recovery (secondary, `double_bridge` only, upper bound).**
  The stricter, original criterion: both true bridges are *exactly* the
  top-`2` scoring set. Retained for completeness because it is the
  bar a real "read off the whole bridge set at once" use case would face,
  but it conflates "one bridge weak" with "the method is confused" and is
  not the primary reported statistic.
- **False-confirmation rate**: fraction of non-bridge candidate pairs
  classified "confirmed" (survival fraction `1.0`).
- **Bridge-confirmed rate**: fraction of replicates in which each true
  bridge is itself classified "confirmed".
- **Bootstrap calibration**: for `confound_trap_observed` and
  `confound_trap_latent` at one representative `(rho_bridge, rho_confound)`
  cell, the bootstrap-confirmed rate for the true bridge vs. the confound
  decoy, checked for correct **ordering** (bridge above decoy) — this
  project's own standing preference, established with the user in
  conversation, for calibration/ordering checks over fixed numeric bands
  (mirroring Stage 5i's own move away from fixed `95%`/`80%` bands to a
  data-derived floor).

## Decision structure

**One hard gate (pipeline integrity):**

- **G1.** The survival-fraction score reproduces the `pMax`-style score's
  top-1 pick in at least `95%` of validation replicates on
  `confound_trap_observed` at every `(rho_bridge, rho_confound, N)` cell
  where both are computed from the identical candidate pool — since both
  are built from the same underlying per-set p-values, a large
  disagreement would indicate an implementation bug (as happened during
  this charter's own preliminary scratch validation: a ranking-direction
  bug was caught and fixed before any conclusion was drawn — see
  Background). `0.95` is kept as proposed (not tightened to Stage 5i's
  `0.999`/`0.99`): unlike Stage 5i's G1/G2, which compared two
  *independently generated* runs (different machines, subject to the
  sampler non-reproducibility diagnosed in D-065), this gate compares two
  statistics computed from the **same** per-set p-values within a single
  run, so near-perfect agreement is structurally expected and `0.95`
  already leaves comfortable room for the rare case where the two scores'
  differing aggregation (a weighted average of per-`k` pass rates vs. a
  single worst-case p-value) picks a different top candidate on a
  close call. If this gate fails, stop and resolve before interpreting
  anything else.

**Descriptive questions (no PROCEED/REASSESS gate, same standing as every
prior R6 charter):**

- **Q1 — Does survival-fraction ranking beat marginal-correlation ranking
  at identifying true bridges when a confound is present and measured?**
  Reported per `(rho_bridge, rho_confound, N)` cell; predeclared reading:
  survival-fraction top-1 rate exceeding marginal-correlation top-1 rate
  by `>= .20` at `>= 80%` of cells is "confirms the preliminary scratch
  finding"; anything less is reported as a partial or non-replication,
  not reframed after the fact.
- **Q2 — Does detection power scale with `N` and bridge strength as
  expected?** Reported as the shape of top-1 recovery rate across the `N`
  and `rho_bridge` grids, per shape — a smooth increasing curve is the
  predeclared expectation; a non-monotonic result is reported as a
  finding, not smoothed over.
- **Q3 — Does the false-confirmation rate shrink toward `0` with `N` when
  the confound is measured, and stay flat when it is not?** This is the
  charter's central predeclared check on the headline limitation
  identified in scratch validation. Predeclared reading: `>= 3x` shrinkage
  from `N=500` to `N=3000` for `confound_trap_observed` and `< 1.5x`
  shrinkage (i.e., materially flat) for `confound_trap_latent` confirms
  the limitation as described; otherwise the limitation is restated per
  the actual pattern found.
- **Q4 — Does a larger conditioning-candidate pool (`larger_clusters`)
  degrade detection relative to the 3-node-cluster shapes?** Reported as a
  direct comparison at matched `(rho_bridge, rho_confound, N)`; no
  threshold predeclared beyond direction and approximate magnitude,
  consistent with this being an open question raised in conversation
  rather than a settled hypothesis.
- **Q5 — Are both bridges recovered in `double_bridge` at a rate
  consistent with the single-bridge rate, or does joint recovery degrade
  disproportionately?** Answered primarily via the per-bridge top-`3`
  recovery rate for each of `double_bridge`'s two bridges, compared
  against the matched single-bridge shape's top-`2` rate at the same
  `(rho_bridge, rho_confound, N)`; the exact-joint-recovery statistic is
  reported alongside as the stricter upper-bound reading.

**Required reporting whatever the outcome**: the full grid, no cell
omitted; the false-confirmation-rate-vs-`N` figure for `confound_trap_
observed` vs. `confound_trap_latent` side by side (this charter's central
exhibit); the bootstrap calibration check; explicit statement of results
for `N=500` labeled "below GOPC's validated range, informational only."

## Explicit non-goals

- **No claim to detect or correct for unmeasured confounding.** Q3's
  predeclared expectation is that the limitation persists — this charter
  documents it quantitatively, it does not attempt to fix it. Any future
  charter proposing a fix (e.g., sensitivity bounds, an explicit
  "possible unmeasured confound" flag) is separate, out of scope here.
  The eventual package documentation and manuscript language must state
  this limitation plainly.
- **No causal-direction claim.** "Explainer" means a variable whose
  conditioning value removes the association statistically; it is not a
  causal mediator claim.
- **No retuning of `fit_gopc`'s own screening or `max_conditioning_size`
  default.** This charter uses them unchanged as the input candidate
  graph.
- **No community-detection algorithm.** As in D-063, community assignment
  is caller-supplied; this charter's shapes have ground-truth communities
  by construction.
- **No non-Gaussian or ordinal data.** Same Gaussian scope as every prior
  R6/Stage-5 charter; a follow-up charter, not this one.
- **No claim of superiority over PC's own `pMax` diagnostic** — Q1
  compares against marginal correlation (the practice this charter argues
  against), not against `pMax`, which G1 treats as a near-equivalent
  sanity check, not a competitor to beat.

## Required evidence

Resolved configuration; this charter's SHA-256 (recorded at freeze);
commit and runtime metadata; raw per-replicate scores (survival fraction,
`pMax`, marginal correlation, bootstrap-confirmed rate where computed) for
every candidate pair at every `(shape, rho_bridge, rho_confound, N)` cell,
no cell omitted; a report presenting G1 and Q1-Q5 with the required
figures above. Archived under
`evidence/stage6_evidence_tiers/stage6a_bridge_validation/`.

## Consequences

If G1 passes and Q1-Q3 replicate the preliminary scratch finding: build
`gopcnet.evidence` (a new top-level module, decided below — not folded
into `gopcnet.metrics`) as a new, additive module (edge-evidence-tier
computation and cross-community bridge ranking), with its own tests,
documentation, and a tutorial section, and add the unmeasured-confounding
limitation to `docs/validated_operating_ranges.md` and any user-facing
documentation as a standing, permanent caveat — not something later
charters are expected to remove. If Q1 does not replicate at the
predeclared threshold, the feature is not built as proposed, and the
scratch finding is recorded in the decision log as a non-replicated
preliminary result, not silently dropped. Either outcome gets its own
decision-log entry (next number after D-065) with this charter's SHA-256
and a link to the evidence directory.

## Resolutions of the pre-freeze questions

1. **Bootstrap replicate count (`B=200`).** Confirmed, kept as proposed.
   It is cheap at this charter's `p <= 9` (the whole widened scratch sweep,
   several thousand replicates across shapes and `N`, ran in under `10`
   seconds), so no reduction is needed even at `2,000` replicates x the
   full grid.
2. **G1 threshold (`0.95`).** Kept as proposed. Justification added
   in-line under Decision structure: this gate compares two statistics
   computed from the same within-run per-set p-values (unlike Stage 5i's
   G1/G2, which compared independently generated runs across machines),
   so `0.95` is already a comfortable, not a lenient, bar.
3. **Confound-strength grid.** Widened to `{0.20, 0.30, 0.40}`. `0.20` was
   chosen, not an arbitrary "weaker" pick, because an exact check of the
   marginal-correlation formulas at this charter's frozen `rho_within =
   0.30` shows it sits right at the boundary where the "trap" (decoy
   marginal correlation exceeding the true bridge's) turns off for the
   weakest bridge and stays off for every stronger bridge in the grid —
   giving a genuine no-trap contrast cell where marginal-correlation
   ranking is *expected* to do fine, alongside the two trap-active cells.
   Justification is recorded in-line under Design.
4. **`double_bridge`'s exact-joint-recovery metric.** Recommendation:
   demote it from primary to secondary/upper-bound, and add a per-bridge
   top-`3` recovery rate as the primary statistic. Reasoning: exact-set
   match conflates "one of two bridges is weak this replicate" with "the
   method is confused," which are different findings a researcher would
   want reported separately; a per-bridge rate is also what a user of the
   eventual feature would actually consult (their own bridge's
   detectability), not whether an unrelated second bridge also landed in
   the top slots the same replicate. The strict joint metric is kept
   alongside as the harder bar, not discarded.
5. **Module naming and placement.** Recommendation: a new top-level
   module, `gopcnet.evidence`, not folded into `gopcnet.metrics`.
   Reasoning: every function currently in `gopcnet.metrics` (D-060
   through D-063 -- fit indices, global descriptives, the network
   comparison test, bridge *centrality*) is a post-hoc summary computed
   from an **already-fitted, final** adjacency matrix. This charter's
   feature is different in kind: it operates on the raw data and the
   *candidate* graph, before or alongside the final prune decision, and
   produces its own parallel edge classification rather than summarizing
   one. D-062's network comparison test was already given its own
   top-level module (`gopcnet.network_comparison`) rather than folded
   into `metrics`, for the same reason -- it is a procedure, not a static
   summary statistic -- and this charter's feature is the same kind of
   case.
