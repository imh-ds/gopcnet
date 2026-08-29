# Methodological Decision Log

## D-001: Proceed from Gaussian MI validation to Stage 1 chartering

Date: 2026-08-28

Stage: R1 / Stage 0.1

Status: PROCEED

Decision timing: Predeclared gate evaluated after results

Question: Is the in-repository bivariate KSG-1 estimator viable at the
intended continuous Gaussian sample-size regime?

Prior specification: `docs/stage0_charter.md` fixed the conditions, 500
replicates, development-only k selection, and validation-only proceed gate
before results were generated.

Evidence: `results/generated/stage0_gaussian/decision.json` records 72,000
estimates, zero estimator errors, selected `k=20`, maximum moderate-signal
absolute bias of 0.0134 nats, maximum moderate-signal RMSE of 0.0452 nats,
Spearman strength ranking of 1.00, and null 95th percentile of 0.0213 nats.

Decision: Proceed to a new frozen Stage 1 charter for tolerant-DPI chain,
measured-fork, and true-triangle motif validation.

Rationale: All predeclared Stage 0.1 validation criteria passed. This decision
is limited to the tested continuous Gaussian estimator regime.

Consequences: Do not add screening, bootstrap, mixed-type, synergy, or public
network API layers. Stage 1 must receive its own DGPs, thresholds, seeds, and
stop/reassess gate before implementation.

## D-002: Reassess tolerant-DPI motif validation

Date: 2026-08-28

Stage: R2 / Stage 1

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does tolerance-modified DPI remove observed transitive dependencies
from continuous Gaussian chains and measured forks without pruning genuine
conditional-dependence triangle edges, for some adjacent tolerance pair?

Prior specification: `docs/stage1_charter.md` froze the chain/fork/triangle
DGPs, `N` grid, strengths, tau grid `[0, .05, .10, .15, .20, .25, .30, .40,
.50]`, 500 replicates, development/validation replicate split, and the
proceed gate (chain/fork TPR `>= .80` and triangle FPR `<= .10` at `N >= 500`
for two adjacent tau values) before results were generated.

Evidence: `results/generated/stage1_dpi/decision.json` records 243,000 raw
estimates, zero estimator/DGP/Cholesky errors, and
`"no eligible development tau pair"`. Pooled development-replicate metrics
(`N in [500, 750, 1000]`) show chain/fork indirect-edge pruning TPR `>= .938`
at every tau, but triangle true-edge pruning FPR never drops below `.117`,
even at `tau = .50`, the top of the frozen grid. See
`docs/stage1_report.md` for the full per-tau breakdown.

Decision: Reassess. Do not select a public default tau, and do not proceed to
Stage 2 candidate-edge screening on this evidence.

Rationale: The binding failure is triangle true-edge over-pruning, not
chain/fork under-pruning or estimator/sample-size failure. Tolerant DPI, as
chartered, cannot reach a jointly passing tau within the tested range; the
FPR floor near `tau = .50` does not improve with `N`, indicating a mechanism
property rather than an incomplete or noisy run. Extrapolating past the
frozen tau grid would not be a valid post hoc adjustment under this charter.

Consequences: Stage 2 candidate-edge screening, bootstrap reproducibility,
and later layers remain blocked. Any further tolerant-DPI work requires a new
charter — for example, a wider or differently shaped tolerance grid, or a
reconsidered pruning rule for the triangle motif — frozen before new results,
per the outline's mechanism-by-mechanism falsification requirement.

## D-003: Reassess conditional-independence motif validation (Stage 1b / R2b)

Date: 2026-08-28

Stage: R2b / Stage 1b

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does pruning by each edge's own conditional-independence test
(Gaussian partial correlation, exact for conditional MI on this DGP) fix the
D-002 failure, where magnitude-ratio DPI could not distinguish a real-but-
weaker triangle edge from a fake indirect one?

Prior specification: `docs/stage1b_charter.md` froze the same chain/fork/
triangle DGPs, `N` grid, strengths, 500 replicates, and development/
validation split as the R2 charter, substituting an `alpha` grid `[.0001,
.001, .005, .01, .05, .10, .20, .30, .50]` and the same proceed gate
structure (chain/fork TPR `>= .80`, triangle FPR `<= .10`, two adjacent
alphas, all validation cells).

Evidence: `results/generated/stage1b_dpi/decision.json` records 243,000 raw
estimates, zero errors, and selection of adjacent pair `(0.05, 0.10)` on
pooled development data, failing one validation criterion (triangle
genuine-edge pruning FPR) at `strong`-family cells: `alpha=.05` at `N=500,
750`, and `alpha=.10` at `N=500`. Unlike D-002, the pooled development
curves for chain/fork TPR and triangle FPR now overlap in a shared feasible
region (`alpha` roughly `[.05, .20]`), and the `balanced`/`moderate`
triangle families pass cleanly. The `strong` family's FPR improves
monotonically with `N` at every alpha (e.g., `alpha=.05`: `.187` at `N=500`
down to `.111` at `N=1000`, development replicates), unlike D-002's
`N`-invariant floor. See `docs/stage1b_report.md` for the full breakdown.
Exploratory (non-gating) tracking of `1 - p_value` as a candidate
confidence-style score (not a validated calibration) against ground truth
gives a pooled Brier score of `.081` against a flat `.25` baseline,
improving with `N`.

Decision: Reassess. Do not select a public default alpha, and do not
proceed to Stage 2 candidate-edge screening on this evidence.

Rationale: This result confirms the D-002 diagnosis — the R2 failure was the
magnitude-ratio comparison confusing "weaker but real" with "fake," not an
inherent limit of DPI-style pruning. Testing each edge's own conditional
dependence resolves two of three triangle fixtures outright and narrows the
third to specific small-`N` cells with a trend, not a floor. That is real
progress, but it does not meet the frozen gate on this grid, and the charter
does not permit selecting a different `N` floor or alpha resolution after
seeing results.

Consequences: Stage 2 and later layers remain blocked. A follow-up charter
extending the `N` floor or refining the alpha grid near `[.05, .10]` — frozen
before new results, per the outline's mechanism-by-mechanism rule — is a
reasonable next step given the trend evidence. Separately, the exploratory
`1 - p_value` score result is promising enough to be worth a dedicated
future charter for a confidence-scored edge representation — one that
would need to include a proper reliability diagram and a prevalence-
adjusted baseline before calling it calibrated — per
`docs/stage1b_charter.md`'s consequences section; this remains an
executive decision, not an automatic next step.

## D-004: Reassess higher-N-floor conditional-independence validation (Stage 1c / R2c)

Date: 2026-08-28

Stage: R2c / Stage 1c

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does raising the gate's minimum sample size from `N = 500` to
`N = 750` resolve D-003's failure, where the `strong`-family triangle FPR
cleared the gate at `N = 750`/`1000` but not `N = 500`, improving
monotonically with `N`?

Prior specification: `docs/stage1c_charter.md` froze R2b's DGP, mechanism,
seeds, and alpha grid, extending `sample_sizes` with `N = 1500, 2000` and
raising the gate floor to `N >= 750`, decided from the shape of the R2b
trend before any new evidence.

Evidence: `results/generated/stage1c_dpi/decision.json` records 324,000 raw
estimates, zero errors. Development selection chose adjacent pair `(0.005,
0.01)`, which fails validation on triangle FPR at `strong`-family cells
`N = 750, 1000`. Reading `strong`-family FPR at fixed `alpha` across the
full extended `N` range (development replicates) shows a clean, continuing
decline — `alpha = .05`: `.187` (`N=500`) to `.015` (`N=2000`); `alpha =
.10`: `.141` to `.007` — confirming the sample-size/power hypothesis
directly. The gate nonetheless failed because development selection scans
`alpha` ascending and returns the first pair whose **pooled** average across
all `N >= 750` and all strengths clears both thresholds; at `alpha =
.005`/`.01`, strong performance at the newly added `N = 1500`/`2000` cells
pulled the pooled average under the FPR threshold even though `N =
750`/`1000` alone remained above it. `(0.05, 0.10)` would have passed every
validation cell individually with real margin but was never reached, because
the ascending scan stops at the first pooled-passing pair. See
`docs/stage1c_report.md` for the full breakdown. An exploratory-score
check on `1 - p_value` (Brier score against a flat baseline, non-gating,
not a calibration claim) stayed stable and well below `.25` across the
full `N` range (`.073`-`.094`).

Decision: Reassess. Do not select a public default alpha or `N` floor, and
do not proceed to Stage 2 candidate-edge screening on this evidence.

Rationale: The charter's scientific question — is the R2b failure a
sample-size/power limitation — is answered yes, clearly, by the fixed-alpha
trend. But the formal PROCEED/REASSESS gate is decided by the frozen
development-selection rule, and that rule's pooled-average selection is
blind to per-`N` variation once a wide, heterogeneous `N` range is pooled
together — the same blind spot D-002 identified between pooled-family and
per-family evidence, now appearing between pooled-`N` and per-`N`. Per this
charter, seeing that `(0.05, 0.10)` would have passed cannot be used to
retroactively substitute it for the rule's actual selection; that would be
exactly the kind of post hoc re-selection the process forbids.

Consequences: Stage 2 and later layers remain blocked. The natural next
charter is a revision to the *development-selection rule itself* — for
example, requiring every individual `N` cell (not just the pooled average)
to clear the threshold before an alpha pair is eligible — frozen before new
results. This is a change to the evaluation methodology, not the pruning
mechanism, which the accumulated R2b/R2c evidence supports well. The
confidence-scored-edge-representation option from D-003 remains open and
unaffected by this result.

## D-005: Reassess per-cell development selection (Stage 1d / R2d)

Date: 2026-08-28

Stage: R2d / Stage 1d

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does requiring every individual `(N, strength)` development cell
to pass (not just the pooled average) find an adjacent alpha pair that R2c's
pooled rule missed?

Prior specification: `docs/stage1d_charter.md` froze a change to the
development-selection rule only — an alpha is eligible only if every
individual cell, `N >= 750`, passes both criteria. DGP, mechanism, seeds,
`N` grid, and alpha grid are unchanged from R2c; R2c's raw evidence is
reused verbatim rather than re-simulated.

Evidence: `results/generated/stage1d_dpi/decision.json` records
`"no eligible development alpha pair"`. Checking every alpha individually:
only `alpha = 0.10` is per-cell eligible, with no adjacent eligible partner.
`alpha = .05` fails only two cells (both `strong`-family, FPR `.117`/`.111`
against the `.10` gate); `alpha = .20` fails several chain/fork TPR cells,
all in the `.76`-`.80` range against the `.80` gate. With 250 development
replicates per cell, the binomial standard error is `~.025` at `.80` and
`~.019` at `.10`; every failing cell above misses its threshold by less
than one standard error. See `docs/stage1d_report.md` for the full
breakdown.

Decision: Reassess. Do not select a public default alpha, and do not
proceed to Stage 2 candidate-edge screening on this evidence.

Rationale: This is a third distinct finding, different in kind from D-002
(structural confound) and D-004 (pooling artifact). The per-cell rule,
honestly applied, finds a single isolated passing alpha surrounded by
near-misses consistent with replicate-count sampling noise rather than a
systematic gap. That points at the development replicate count (250 per
cell) being too small for a per-cell decision rule at this alpha grid's
resolution, not at a remaining flaw in the conditional-independence
mechanism, which by this point has been supported by three converging
lines of evidence (D-003's balanced/moderate pass, D-004's power trend to
near-zero FPR, and D-005's isolated-but-clean single point).

Consequences: Stage 2 and later layers remain blocked. Two legitimate next
directions, each requiring its own charter frozen before new results: (a)
more development replicates (the mechanism and grid are unchanged, so this
is a straightforward re-run at higher replicate count, not a new design),
or (b) a coarser alpha grid step that does not require resolving a boundary
this fine. Given the accumulated evidence, this looks like a matter of
statistical resolution rather than a mechanism or methodology problem. The
confidence-scored-edge-representation option from D-003 remains open and
unaffected by this result.

## D-006: Reassess higher-replicate-count per-cell selection (Stage 1e / R2e)

Date: 2026-08-28

Stage: R2e / Stage 1e

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does quadrupling development replicates (250 to 1000) resolve
D-005's near-misses at `alpha = .05` and `alpha = .20`, which were each
smaller than one standard error at 250 replicates?

Prior specification: `docs/stage1e_charter.md` froze R2d's DGP, mechanism,
`N` grid, alpha grid, and per-cell selection rule, increasing replicates
from 500 to 2000 (development 0-999, validation 1000-1999) — a statistical-
power change to the evaluation, not a new design, decided from the observed
noise magnitude in D-005.

Evidence: `results/generated/stage1e_dpi/decision.json` records 1,296,000
raw rows, zero errors, and again `"no eligible development alpha pair"`:
only `alpha = 0.10` passes every cell, with no adjacent partner. But the
extra replicates changed the picture rather than merely repeating it. At
1000 development replicates (SE `~.0095` for FPR at `.10`; `~.0126` for TPR
at `.80`): `alpha = .05`'s one remaining failing cell (`strong` family,
`N = 750`) now misses by `.128` against the `.10` gate — nearly 3 standard
errors, a real failure, not noise (it was `<1` SE at 250 replicates).
`alpha = .20`'s failing chain/fork TPR cells dropped from 12 to 8, and most
remaining misses are now well under 1 SE, consistent with convergence
toward passing, though a couple remain marginal (up to `1.26` SE). See
`docs/stage1e_report.md` for the full breakdown. An exploratory-score
check on `1 - p_value` (Brier score, not a calibration claim) remained
stable (`.074`-`.096` by `N`, pooled `.080`),
consistent with R2c/R2d.

Decision: Reassess. Do not select a public default alpha, and do not
proceed to Stage 2 candidate-edge screening on this evidence.

Rationale: More replicates sharpened the boundary rather than dissolving
it into noise, which is itself informative: `alpha = .05` is now a
confirmed real failure, while `.20`'s issues are shrinking but not fully
resolved. This is consistent with a real, narrow valid region sitting near
`alpha = .10` that the frozen grid's coarse steps (`.05` to `.10` to `.20`)
straddle without another tested point landing inside it. Per
`docs/stage1e_charter.md`'s consequences, this is now a grid-resolution
problem, not a replicate-count problem — more replicates would sharpen the
picture further but would not manufacture an adjacent passing pair where
the grid has no point to land on.

Consequences: Stage 2 and later layers remain blocked. The next charter
should add finer alpha resolution between `.05` and `.20` (e.g. `.06`
through `.19` in fine steps) rather than increasing replicates again,
frozen before new results. Given four converging rounds of evidence
(D-003's balanced/moderate pass, D-004's power trend to near-zero FPR,
D-005's isolated clean point, D-006's sharpening boundary), the mechanism
itself is well supported; what remains is locating the passing alpha
region precisely enough to select an adjacent pair. The confidence-scored-
edge-representation option from D-003 remains open and unaffected.

## D-007: Reassess fine alpha-resolution per-cell selection (Stage 1f / R2f)

Date: 2026-08-28

Stage: R2f / Stage 1f

Status: REASSESS

Decision timing: Predeclared gate evaluated after results

Question: Does a 0.01-resolution alpha grid across `[.06, .25]` contain an
adjacent pair that passes the per-cell development-and-validation gate,
where the coarse grid was too widely spaced to find one?

Prior specification: `docs/stage1f_charter.md` froze R2e's DGP, mechanism,
`N` grid, replicate count, and per-cell selection rule, narrowing the
alpha grid to 20 points at 0.01 steps spanning the region bounded by R2e's
confirmed failure at `.05` and decisive failure at `.30`.

Evidence: `results/generated/stage1f_dpi/decision.json` records 2,880,000
raw rows, zero errors. Development selection found adjacent pair `(0.09,
0.10)`, which fails validation at exactly one cell (`strong` family,
`N = 750`, `alpha = 0.09`, FPR `.104` against the `.10` gate) by `.004` —
under half a standard error at 1000 replicates (`SE ~ .0095`), the smallest
margin failure in this line of charters. Reading the same cell across
`alpha = .08`-`.11` on both development and validation data shows `alpha =
0.09` was development-eligible only by a `.008` margin (also under 1 SE)
and landed on the wrong side of the gate on independent validation data,
while `alpha = 0.10` and `0.11` both hold comfortably on both development
and validation. A pair of `(0.10, 0.11)` was never evaluated against
validation, because the frozen selection rule returns the first ascending
adjacent pair that is development-eligible, and `(0.09, 0.10)` qualified
first — the rule has no way to prefer a pair with a larger, more robust
margin over one that barely and noisily cleared the development threshold.
See `docs/stage1f_report.md` for the full breakdown.

Decision: Reassess. Do not select a public default alpha, and do not
proceed to Stage 2 candidate-edge screening on this evidence.

Rationale: This is a second, distinct selection-methodology gap, different
from D-004's pooling artifact: a "first eligible pair wins" rule offers no
protection against selecting a pair whose eligibility was itself a
coin-flip-margin call. Unlike D-002's structural confound or D-006's
grid-resolution gap, there is now strong, specific evidence (not merely a
trend) that an untested-on-validation pair in the same grid would pass.
Per this charter, that evidence cannot be used to retroactively substitute
`(0.10, 0.11)` for the rule's actual selection.

Consequences: Stage 2 and later layers remain blocked. The next charter
should revise the selection rule to prefer development-eligible pairs with
adequate margin above the threshold (not merely the first pair found) —
frozen before new results, reusing R2f's existing evidence rather than
re-simulating, exactly as R2d reused R2c's. This is the third selection-
methodology fix in this line (after D-004's pooling correction and R2d's
per-cell correction), on top of six rounds of accumulated support for the
underlying mechanism. The confidence-scored-edge-representation option
from D-003 remains open and unaffected.

## D-008: Proceed on margin-robust selection (Stage 1g / R2g)

Date: 2026-08-29

Stage: R2g / Stage 1

Status: PROCEED

Decision timing: Predeclared gate evaluated after results

Question: Does selecting the adjacent development-eligible alpha pair with
the largest worst-case margin, rather than the first eligible pair found,
yield a pair that passes validation with real margin?

Prior specification: `docs/stage1g_charter.md` froze a selection-rule
change only, reusing R2f's raw evidence verbatim: among adjacent alpha
pairs where both members individually pass every `(N, strength)` cell,
select the pair maximizing the minimum cell margin across both members,
rather than the lexicographically first such pair.

Evidence: `results/generated/stage1g_dpi/decision.json` records
`"status": "PROCEED"`, selected pair `(0.14, 0.15)`. Every validation cell
(all three triangle families, `N in [750, 1000, 1500, 2000]`, all three
strengths, both alpha values) passes individually, with a worst-case
chain/fork TPR margin of `.031` above the `.80` gate and a worst-case
triangle FPR margin of `.021` below the `.10` gate — both well outside the
`~.01` standard error at 1000 validation replicates. An exploratory-score
check on `1 - p_value` (Brier score against ground truth, not a
calibration claim) remained stable at `.074`-`.096` by `N`, pooled `.080`,
consistent with every prior
round. `(0.10, 0.11)`, flagged as a promising candidate in D-007, was not
selected; the margin-robust rule found `(0.14, 0.15)` has more worst-case
slack across the full cell grid, not just at the one cell that broke
`(0.09, 0.10)`. See `docs/stage1g_report.md` for the full breakdown.

Decision: Proceed. This closes the R2 through R2g line of Stage 1
tolerant/conditional-independence-DPI motif validation. Stage 2
candidate-edge screening may be planned.

Rationale: This is the first PROCEED in this line, reached only after
diagnosing and correcting three separate flaws — a structural confound in
magnitude-ratio DPI (D-002, resolved by switching to conditional
independence at D-003), a pooled-average selection artifact (D-004,
resolved by per-cell selection at D-005), and a "first eligible pair"
selection artifact with no margin awareness (D-007, resolved here). Seven
prior rounds of REASSESS were each a legitimate falsification of a
specific, narrow hypothesis, not repeated failures of the same claim; the
mechanism itself was never the thing that kept failing.

Consequences: The validated scope is specifically continuous Gaussian
data, `N >= 750`, three-node motifs, conditional-independence pruning via
Gaussian partial correlation, `alpha` near `0.14`-`0.15`. This does not
select a public default alpha beyond this pair and does not by itself fix
a specific Stage 2 design; Stage 2 candidate-edge screening must receive
its own frozen charter, DGP, and gate before implementation, per the
outline's mechanism-by-mechanism rule. The confidence-scored-edge-
representation option from D-003 remains open; the exploratory `1 -
p_value` score has stayed informative (consistently low Brier score
against a flat baseline) across every round from R2b through R2g, though
this is not itself a calibration finding — a reliability diagram and a
prevalence-adjusted baseline would be needed before making that claim.

## D-009: Per-N alpha table (Stage 1h / R2h)

Date: 2026-08-29

Stage: R2h / Stage 1

Status: Per-N table (no single global status — see rationale)

Decision timing: Predeclared gate evaluated after results

Question: Does each sample size have its own passing alpha region, and if
so, what is the relationship between `N` and the validated alpha?

Prior specification: `docs/stage1h_charter.md` froze an executive change
to the gate structure: select and validate an alpha pair independently per
`N`, rather than requiring one pair across a pooled `N` range. Extended
`N` to `[100, 200, 300, 500, 750, 1000, 1500, 2000, 3000]` and widened the
alpha grid to `[.0001 ... .50]` (23 points) to give smaller `N` a fair
search.

Evidence: `results/generated/stage1h_dpi/decision.json` records 3,726,000
raw rows, zero errors, and a per-`N` table:

| N | status | alpha pair | margin |
|---|---|---|---|
| 100 | REASSESS | none | — |
| 200 | REASSESS | none | — |
| 300 | REASSESS | none | — |
| 500 | REASSESS | none | — |
| 750 | PROCEED | (0.14, 0.16) | .032 |
| 1000 | PROCEED | (0.12, 0.14) | .041 |
| 1500 | PROCEED | (0.10, 0.12) | .075 |
| 2000 | PROCEED | (0.08, 0.10) | .087 |
| 3000 | PROCEED | (0.06, 0.08) | .099 |

At `N >= 750`, alpha decreases and margin increases monotonically with
`N` — a clean, usable trend. Below `750`, the worst-case TPR- and
FPR-satisfying alpha regions were checked for overlap across the full
alpha sweep: `N = 100, 200, 300` show a wide, decisive gap (raising alpha
enough to fix triangle FPR destroys chain/fork TPR long before the two
regions meet); `N = 500` shows a gap of only one grid step (`.18` passes
TPR, `.20` passes FPR), plausibly resolvable with finer resolution but
likely thin-margin even so. See `docs/stage1h_report.md` for the full
breakdown.

Decision: This charter does not produce a single PROCEED/REASSESS by
design. It produces the per-`N` evidence table above, which is the
required input to a future charter proposing a specific `alpha(N)`
default rule.

Rationale: Different sample sizes needed, and got, different treatment,
per this charter's explicit executive framing. The `N >= 750` finding
strengthens D-008 with five sample sizes now showing a clean, monotonic
`alpha`-vs-`N` shape instead of one — but this is a predeclared
**reanalysis under a new per-N selection rule, not five independent fresh
replications**: `N = 750, 1000, 1500, 2000` reuse the exact same
simulated data as R2c through R2g (identical seeds; only `N = 3000` is
genuinely new data). The value of this result is the new selection rule
and the shape it reveals, not additional independent statistical power at
those four `N` values. The `N < 750` findings are informative in their own
right, scoped to the alpha grid actually tested (`[.0001, .50]` at this
resolution): `N <= 300` shows no alpha in that grid where both criteria
hold at once — a decisive structural limit within the tested range, not a
tuning problem, though not a proof about every conceivable alpha value
outside it. `N = 500` quantitatively confirms — rather than merely
re-asserts — R2c's original choice of a `750` floor, by showing `500`
sits almost exactly on the boundary rather than comfortably on either
side of it.

Consequences: A future charter may (a) fit and freeze a specific
`alpha(N)` default rule from the `N >= 750` table (e.g., a smooth
decreasing function of `N`, validated at genuinely new, held-out `N`
values), and/or (b) check whether the `N = 500` gap closes with finer
alpha resolution, purely out of curiosity about the boundary shape —
`N <= 300` does not warrant that check within the tested grid, since its
gap is wide and decisive there. Neither is required before Stage 2
planning, which may proceed using the `N >= 750` result from D-008 and
this table's reanalysis of it. The confidence-scored-edge-representation
option from D-003 remains open; the exploratory `1 - p_value` score
stayed informative (stable Brier score against a flat baseline, not a
calibration finding) across the full `100`-`3000` range tested here.

## D-010: Locate the N=500-750 crossover (Stage 1i / R2i)

Date: 2026-08-29

Stage: R2i / Stage 1

Status: Per-N table (no single global status)

Decision timing: Predeclared gate evaluated after results

Question: `N=500` came within one grid step of passing (D-009) while
`N=750` passed comfortably (D-008); does the actual minimum viable `N`
lie somewhere in the untested gap between them?

Prior specification: `docs/stage1i_charter.md` froze fresh simulation for
`N = [550, 600, 650, 700]`, reusing R2h's `N=500, 750` rows as bookends,
under the same per-N margin-robust selection rule as R2h/R2g.

Evidence: `results/generated/stage1i_dpi/decision.json` records 2,484,000
raw rows (1,656,000 newly simulated), zero errors:

| N | status | alpha pair | margin |
|---|---|---|---|
| 500 | REASSESS | none | — |
| 550 | REASSESS | none | — |
| 600 | REASSESS | none | — |
| 650 | REASSESS | (0.14, 0.16), failed validation | .018 (dev) |
| 700 | PROCEED | (0.14, 0.16) | .012 |
| 750 | PROCEED | (0.14, 0.16) | .032 |

`N <= 600` finds no development-eligible pair at all. `N=650` is a
near-miss (development-eligible, fails validation). `N=700` is the first
sample size to PROCEED, but with a margin (`.012`) close to the `~.0095`
-`.0126` standard error established at D-006/D-009 — a real pass, not a
comfortable one. `N=750` remains the first sample size with a clearly
robust margin (`.032`, roughly `3`-`4`x the noise level). See
`docs/stage1i_report.md` for the full breakdown.

Decision: The transition is broadly monotonic (REASSESS through `600`,
near-miss at `650`, thin-margin PROCEED at `700`, comfortable PROCEED at
`750`) rather than the noisy, non-monotonic pattern that would have
warranted treating the gap as unresolved. `N=700` is a legitimate,
evidence-based floor for a thin-margin use case; `N=750` remains the floor
for a comfortable, noise-robust margin.

Rationale: The gap was real, not an artifact of the round number `750`
chosen in D-004 — but it was also narrower than it might have been: `500`
through `600` are decisively not viable, and the actual crossover sits in
a tight `650`-`700` band, not spread evenly across the whole `500`-`750`
range.

Consequences: `docs/validated_operating_ranges.md` should record both
`700` (thin margin) and `750` (comfortable margin) explicitly, rather than
collapsing to one number, so a downstream user can choose based on how
much margin they need. No further replicate or grid-resolution charter is
required to act on this finding; `N=700`'s thin margin is disclosed as
such rather than treated as fully resolved.

## D-011: Recommend N=750 as the default floor, not N=700

Date: 2026-08-29

Stage: Policy (post-Stage 1, using D-010's evidence; no new simulation)

Status: Executive decision

Decision timing: Made after seeing D-010's results, since it is an
interpretation of existing evidence, not a predeclared statistical gate

Question: D-010 showed both `N=700` and `N=750` PROCEED. Should the
project recommend one as the default floor for autonomous use?

Evidence: `N=700`'s validation margin (`.012`) is roughly `1.3` standard
errors above the pass/fail line at 1000 replicates; `N=750`'s (`.032`) is
roughly `3`-`4` standard errors. `N=650`, one step below `700`, fails.
This project has twice before (D-005, D-007) seen a margin of this size
flip sides on an independent re-check.

Decision: Recommend `N >= 750` as the default floor for autonomous DPI
edge-pruning decisions. Retain `N = 700` as a documented, available
option for a researcher who cannot collect more data and explicitly
accepts the thinner, noise-adjacent margin — not withheld, but not the
default.

Rationale: An "autonomous use" floor's value is specifically that a
researcher does not need to inspect or second-guess it case by case
(per `docs/validated_operating_ranges.md`'s stated stance). A margin of
`1.3` SE, sitting one step past a demonstrated failure at `N=650`,
partially defeats that purpose even though it technically passed its own
validation split. This is a judgment call about acceptable risk, not a
new empirical finding — the underlying D-010 evidence is unchanged and
both options remain visible.

Consequences: `docs/validated_operating_ranges.md` records this
explicitly (see "Recommended default floor" section). Any future Stage 2+
work, or production default-selection logic, should treat `750` as the
recommended floor unless a specific downstream use case has reason to
accept `700`'s thinner margin instead.
