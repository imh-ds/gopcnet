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

## D-012: Fit and validate an alpha(N) formula (Stage 1j / R2j)

Date: 2026-08-29

Stage: R2j / Stage 1

Status: PROCEED

Decision timing: Predeclared gate evaluated after results (fitting form
selection was also predeclared and required no results-dependent choice,
since `linear_log_n` won outright)

Question: Can a smooth `alpha(N)` formula, fit only from the six known
validated points, correctly predict a working alpha at sample sizes it
never saw?

Prior specification: `docs/stage1j_charter.md` froze four candidate
functional forms, a fitting procedure using the six D-008/D-009/D-010
points (no new simulation), and a held-out validation requirement at four
interpolated, previously-untested `N` values (`900, 1250, 1750, 2500`),
gated on the single predicted alpha clearing a `.02` margin — not merely
passing — at every held-out `N`.

Evidence: `linear_log_n` fit the six known points with `R^2 = .997`, more
than `.005` ahead of every other candidate (linear `N`: `.952`; power
law: `.987`; inverse-sqrt: `.989`) — selected outright, no tiebreak
needed. `results/generated/stage1j_dpi/decision.json` records 72,000 raw
rows, zero errors, and PROCEED at all four held-out `N`, with margins
increasing with `N` exactly as every prior charter in this line found:
`900`: `.039`; `1250`: `.069`; `1750`: `.079`; `2500`: `.097`. None are
thin-margin passes. See `docs/stage1j_report.md` for the full breakdown.

Decision: Proceed. The fitted formula `alpha(N) = 0.5222 - 0.0566 *
ln(N)` is a candidate default rule, validated by interpolation across
`N in [700, 3000]`.

Rationale: Curve-fit quality alone would not have been sufficient
evidence — a formula can fit six known points closely and still fail
between them. It did not fail here: every held-out prediction not only
passed but passed comfortably, which is the actual claim a default rule
needs to support.

Consequences: This is a candidate for a production default, not itself
one — adopting it requires a separate, later decision, consistent with
every prior "this stage does not authorize the next" boundary in this
line. The formula must not be extrapolated below `N=700` (the D-010/D-011
floor) or above `N=3000` (the edge of the tested range); both are outside
this charter's validated scope. `docs/validated_operating_ranges.md`
should record the formula alongside the existing per-`N` table as a
candidate default, not a replacement for the floor recommendation in
D-011.

## D-013: Candidate-edge screening passes in isolation (Stage 2 / R3)

Date: 2026-08-29

Stage: R3 / Stage 2

Status: PROCEED at both tested `N`

Decision timing: Predeclared gate evaluated after results

Question: Does per-pair Fisher-z screening on raw correlation correctly
separate genuinely-associated pairs from genuinely-independent ones in a
`p=15` network, at Stage 1's validated `N`, and is BH correction
necessary to do so?

Prior specification: `docs/stage2_charter.md` froze a known-ground-truth
`p=15` network (chain, fork, `moderate` triangle embedded in 6 noise
columns: 9 true candidate pairs, 96 null pairs), `N = [750, 1500]`, seven
candidate rules (uncorrected `alpha in [.001, .005, .01, .05, .10]`, BH
`q in [.05, .10]`), gated on development recall `>= .80` and FDR `<= .10`,
validated independently per `N`, with a predeclared tiebreak preferring
the simplest eligible rule.

Evidence: `results/generated/stage2_screening/decision.json` records
28,000 raw rows, zero errors, and PROCEED at both `N`, selecting
uncorrected `alpha = .001` at both (validation recall `.9999`/`1.0000`,
FDR `.0121`/`.0106`). The full operating table shows recall is
essentially `1.0` at *every* tested threshold — power was never the
constraint — while FDR scales with `alpha` in the direction the charter's
pre-registered back-of-envelope arithmetic anticipated (`alpha=.001`
predicted `~.012`, observed `.011`-`.012`) — a successful pre-specified
prediction of the FDR/alpha relationship's shape, not an independent
confirmation, since the arithmetic and the simulation share the same
96:9 null:true DGP assumption. Both BH thresholds also pass at both `N`,
but lose the tiebreak to the simpler uncorrected rule. See
`docs/stage2_report.md` for the full breakdown.

**Correction (2026-08-30, second peer review):** the FDR figures above
were originally computed as a mean of each replicate's own FDR ratio
(`.0109`/`.0094`), which does not match this charter's frozen pooled
definition ("fraction of *all* flagged pairs, across all 96+9 possible
pairs, that are actually null" — i.e. total false discoveries / total
discoveries, summed across replicates, not averaged per-replicate
ratios). `src/mintnet/experiments/stage2_reporting.py`'s `_rule_metrics`
and `aggregate_stage2` were corrected to pool by summed counts
(`src/mintnet/experiments/stage2.py`'s raw evidence now also records
`true_positives`/`false_positives`/`total_flagged` per row so this is
possible), and Stage 2's evidence was regenerated
(`results/generated/stage2_screening/`). The corrected pooled FDR is
`.0121` at `N=750` and `.0106` at `N=1500` — both still comfortably under
the `.10` gate, so this decision's PROCEED status and selected rule
(`uncorrected, alpha=.001`, at both `N`) are unchanged. The two FDR
values happened to move in opposite directions under the fix (`N=750`'s
figure rose, `N=1500`'s fell), consistent with mean-of-ratios and
pooled-counts being genuinely different statistics rather than the same
number reached two ways.

Decision: Proceed. Screening validated in isolation at `p=15`,
`N in [750, 1500]`.

Rationale: This is the first Stage 2 charter to PROCEED on its first
attempt, unlike every Stage 1 charter after R2. The charter's
pre-registered arithmetic anticipating the FDR/alpha relationship before
any simulation ran (given the 96:9 null:true imbalance) matched the
observed results closely — a successful pre-specified prediction, which
is evidence the mechanism and its evaluation are well understood, though
not independent confirmation given the shared DGP assumption noted above.

Consequences: This does not authorize composing screening with Stage 1's
validated DPI pruning into one pipeline — per the outline's Section 2.1,
that composition is its own mechanism-interaction question and needs its
own charter. It also does not authorize `p=30` or other network sizes,
which remain untested. `docs/validated_operating_ranges.md` should record
this component's validated range (`p=15`, `N in [750, 1500]`, uncorrected
`alpha=.001` sufficient, BH available but not required).

## D-014: Screening + DPI composition passes (Stage 2b / R3b)

Date: 2026-08-29

Stage: R3b / Stage 2

Status: PROCEED at both tested `N`

Decision timing: Predeclared gate evaluated after results, including a
predeclared quantitative expectation (final false-edge rate should track
screening's own rate, stated before running anything)

Question: Does composing Stage 2's validated screening with Stage 1's
validated DPI pruning, applied only within clean 3-node candidate triads,
correctly recover the true network structure end to end?

Prior specification: `docs/stage2b_charter.md` froze the pipeline
(screen at D-013's winning `alpha=.001`; group candidate edges into
connected components; apply DPI, at the D-012 formula's `alpha(N)`, only
within components that are exactly a 3-node candidate triad; pass every
other shape through unmodified), reusing Stage 2's exact `p=15` DGP and
`N in [750, 1500]` specifically so "which variable to condition on" has
an unambiguous answer.

Evidence: `results/generated/stage2b_composition/decision.json` records
4,000 raw rows, zero errors, PROCEED at both `N`:

| N | indirect TPR | true-edge FPR | screening FER | final FER | triad rate |
|---|---|---|---|---|---|
| 750 | .818 | .0053 | .00115 | .00115 | .961 |
| 1500 | .861 | .0004 | .00100 | .00100 | .963 |

`screening_false_edge_rate` and `final_false_edge_rate` are identical at
both `N`, confirming the charter's predeclared expectation exactly: DPI
essentially never rescues a screening false positive, because false
positives are almost always isolated single edges with no shared
neighbor to condition on. Indirect-edge TPR (`.818`/`.861`) is a little
below Stage 1's isolated-motif numbers at similar alpha (D-009: `~.85`-
`.87` at `N=750`), explained by the `~4%` of replicates (`triad_rate ~
.96`) where a true motif's candidate component was not a clean triad and
so skipped DPI entirely. See `docs/stage2b_report.md` for the full
breakdown.

Decision: Proceed. The composed pipeline is validated for disjoint,
non-overlapping 3-node motifs at `p=15`, `N in [750, 1500]`.

Rationale: This is the first charter to test an actual interaction
between two independently-validated mechanisms, and the result is not
just a pass but an explained one — both the "no false-edge rescue" and
the "small TPR gap" findings match predeclared or immediately traceable
mechanistic reasons, rather than being accepted as an opaque aggregate
number the way early Stage 1 charters sometimes had to be before their
underlying cause was understood.

Consequences: This does not validate general-shaped candidate graphs —
overlapping motifs, hub variables, or components larger than 3 nodes
remain a distinct, open, harder question needing its own DGP and charter
before Stage 3 (bootstrap) or a full continuous MVP can be responsibly
attempted. `docs/validated_operating_ranges.md` should record the
composed pipeline's validated range separately from screening-alone
(D-013) and DPI-alone (D-008/D-012), since composition was not guaranteed
by either mechanism's individual validation.

## D-015: Multi-variable conditioning passes on a hub motif (Stage 1k / R3c)

Date: 2026-08-29

Stage: R3c / Stage 1

Status: PROCEED at both tested `N`

Decision timing: Predeclared gate evaluated after results; a quick
non-charter simulation check was run before freezing to confirm the
design was well-posed (not treated as evidence, only as a sanity check
before committing compute)

Question: Does conditioning on every other node in a candidate component
— the direct generalization of Stage 1's one-variable partial
correlation — correctly separate direct from indirect edges when a
component has more than 3 nodes, and does the existing D-012 `alpha(N)`
formula (fit only for one-variable conditioning) still work unmodified?

Prior specification: `docs/stage1k_charter.md` froze a minimal 4-node hub
DGP (1 hub, 3 independent children), `N in [750, 1500]`, testing the
D-012 formula's predicted `alpha_hat` directly (no new grid search),
gated on indirect-edge TPR `>= .80`, true-edge FPR `<= .10`, and a `.02`
required margin on both.

Evidence: `results/generated/stage1k_hub/decision.json` records 4,000 raw
rows, zero errors, PROCEED at both `N`: `750` (TPR `.854`, FPR `0`,
margin `.054`); `1500` (TPR `.887`, FPR `0`, margin `.087`). Both clear
the required margin comfortably, not as thin-margin passes. A
pre-charter sanity simulation predicted `TPR ~ .858`/`.882`, `FPR = 0` —
the actual results landed almost exactly there. See
`docs/stage1k_report.md` for the full breakdown.

Decision: Proceed. Multi-variable conditioning, using the unmodified
D-012 formula, is validated for this 4-node hub shape at `N in [750,
1500]`.

Rationale: This is a genuinely informative, non-obvious result: a formula
fit only against one-variable-conditioning evidence did not need
refitting to also work for two-variable conditioning. That the actual
outcome matched a quick pre-registered simulation almost exactly is
further evidence the mechanism is understood, not merely lucky —
consistent with D-013's similar experience.

Consequences: This validates the multi-variable conditioning mechanism
only for the hub shape tested (one shared cause, several independent
children) — not for components formed by two motifs sharing a node, or
larger components generally, which remain open questions for a future
charter. Combined with D-014, the pieces needed to extend Stage 2b's
composed pipeline beyond exact 3-node triads to hub-shaped candidate
components now exist, though wiring that extension into the actual
pipeline (`mintnet.pipeline.compose`) has not itself been done or
chartered yet.

## D-016: Wired hub conditioning into the pipeline; mixed-shape composition passes (R3d)

Date: 2026-08-29

Stage: R3d / Stage 2

Status: PROCEED at both tested `N`

Decision timing: Predeclared gate evaluated after results; a pre-charter
simulation check (1500 replicates) was run before freezing to catch a
misleading noisy estimate from an even smaller initial check, not treated
as evidence itself

Question: Does the composed pipeline correctly handle a single network
containing both a 3-node triad shape and a 4-node hub-clique shape at
once, using one general conditioning rule for both?

Two things happened here, in order:

1. **Code generalization.** `mintnet.pipeline.compose` was rewritten to
   replace its triad-only special case with one general rule: apply
   multi-variable conditioning within any candidate component that is a
   validated clique shape (size 3, from D-008 through D-012, or size 4,
   from D-015); pass through every other shape unmodified. This was
   justified by proving the general multi-variable mechanism
   (`mintnet.dpi.multi_conditional`) is numerically identical to Stage
   1's original one-variable closed-form when there is exactly one
   conditioning variable (see `tests/unit/test_multi_conditional.py`),
   and verified safe by re-running D-014's exact original configuration
   through the new code and confirming byte-for-byte identical
   `decision.json` output before proceeding.
2. **New evidence.** `docs/stage2c_charter.md` froze a `p=15` network
   combining Stage 2b's chain/fork motifs with Stage 1k's hub motif in a
   single network (replacing the triangle from D-014), `N in [750,
   1500]`, same screening/DPI alphas as D-014.

Evidence: `results/generated/stage2c_composition/decision.json` records
4,000 raw rows, zero errors, PROCEED at both `N`:

| N | indirect TPR | true-edge FPR | screening FER | final FER | shape-validated rate |
|---|---|---|---|---|---|
| 750 | .820 | .000 | .00101 | .00101 | .965 |
| 1500 | .853 | .000 | .00120 | .00120 | .958 |

Every prior finding replicated: screening and final false-edge rates are
identical at `N=1500` (`.0012043` both) and nearly identical at `N=750`
(screening `.00101075` vs. final `.00100000` — the displayed 5-figure
table above rounds this to the same `.00101` at both, masking a real but
tiny difference; corrected 2026-08-30, second peer review) — D-014's "no
rescue" finding, essentially confirmed alongside hub components too;
true-edge retention is perfect; the `~.96` shape-validated rate matches
D-014's triad-only rate closely. The `N=750` indirect TPR (`.820`)
landed almost exactly on a pre-charter 1500-replicate simulation's
prediction (`.823 +/- .005`) — a successful pre-specified prediction,
not independent evidence against an unpredicted interaction, since the
pre-charter check shares the same DGP and code assumptions as the frozen
run. See `docs/stage2c_report.md` for the full breakdown.

Decision: Proceed. The generalized pipeline is validated for networks
mixing 3-node triad and 4-node hub-clique candidate components, at
`p=15`, `N in [750, 1500]`.

Rationale: This closes the loop opened at D-015's consequences: the hub
mechanism is now not just validated in isolation but actually wired into,
and confirmed working within, the composed pipeline — and confirmed not
to interact badly with the triad mechanism it now runs alongside.

Consequences: `docs/validated_operating_ranges.md` should record the
generalized composed pipeline's validated range, noting it now covers
mixed 3-node/4-node candidate components, not just uniform triads.
Non-clique components, cliques of any other size, larger networks, and
components sharing variables across motifs remain untested and out of
scope.

## D-017: Multi-variable conditioning generalizes to shared-node overlap (R3e)

Date: 2026-08-29

Stage: R3e / Stage 1

Status: PROCEED at both tested `N`

Decision timing: Predeclared gate evaluated after results; a pre-charter
power calculation (not simulation this time, closed-form) flagged that
screening's detection of the weak cross-branch correlation is unreliable
at `N=750` (`~66%` power) vs. `N=1500` (`~98%`) — this was used to scope
the charter to the conditioning mechanism in isolation, not to predict
its outcome

Question: Does "condition on all other nodes in the candidate component"
generalize to a topology genuinely different from Stage 1k's hub/star —
two triangles overlapping at a single shared node — using the existing
D-012 `alpha(N)` formula unmodified?

Prior specification: `docs/stage1l_charter.md` froze a 5-variable DGP
(two `balanced`-style triangles sharing node 2), `N in [750, 1500]`,
testing the D-012 formula's predicted `alpha_hat` directly against a
clean, hand-fed 5-node component (bypassing whether screening would
actually detect it that cleanly — explicitly out of scope, deferred to a
future wiring charter mirroring Stage 1k -> Stage 2c).

Evidence: `results/generated/stage1l_overlap/decision.json` records 4,000
raw rows, zero errors, PROCEED at both `N`: `750` (TPR `.858`, FPR `0`,
margin `.058`); `1500` (TPR `.894`, FPR `0`, margin `.094`). Both clear
the required margin comfortably. A pre-charter 1000-replicate simulation
predicted `TPR ~ .847`/`.884` — close to the actual result. See
`docs/stage1l_report.md` for the full breakdown.

Decision: Proceed. Multi-variable conditioning generalizes to shared-node
overlap topology, at `N in [750, 1500]`, using the unmodified D-012
formula.

Rationale: This is now the second distinct topology (after the hub) where
the same general rule and the same formula work without modification,
strengthening the case that the conditioning mechanism itself is broadly
general rather than validated only for star-shaped structures.

Consequences: This does **not** extend `VALIDATED_CLIQUE_SIZES` or wire
anything into `mintnet.pipeline.compose` — unlike the hub case, this
DGP's cross-branch signal is weak enough that screening frequently will
not produce a clean 5-node candidate clique at `N=750` (the pre-charter
power calculation), so a wiring charter here would need to separately
characterize how often a clean shape actually forms, not just assume it
does because the mechanism works when handed one. That remains a distinct
future charter. `docs/validated_operating_ranges.md` should record this
mechanism-level result separately from any pipeline-wiring claim.

## D-018: Overlap wiring matches the pre-specified screening-power split prediction (R3f)

Date: 2026-08-29

Stage: R3f / Stage 2

Status: REASSESS at `N=750`, PROCEED at `N=1500` (matches the pre-specified split prediction)

Decision timing: Predeclared gate evaluated after results; the specific
split outcome was predicted, in writing, by a pre-charter simulation
before any frozen results existed — this is a successful pre-specified
prediction, not independent confirmation, since the pre-charter
simulation and the frozen run share the same DGP and code assumptions
(second peer review, 2026-08-30; see the correction note below)

Question: Does the shared-node-overlap motif, embedded in a network and
run through the full screen-then-prune pipeline (with
`VALIDATED_CLIQUE_SIZES` extended to include 5, per D-017), behave the
way its screening-power limitation predicted?

Prior specification: `docs/stage2d_charter.md` froze a `p=15` network
(chain, fork, the overlap motif, 4 noise columns), extended
`VALIDATED_CLIQUE_SIZES` to `{3, 4, 5}`, and gated **per motif**
(chain/fork/overlap TPR each individually `>= .80`, not pooled — a
deliberate design choice to avoid the D-004 pooling blind spot). It
explicitly predicted, before results: `N=750` overlap TPR `~.59`,
clean-clique rate `~26%` (REASSESS); `N=1500` overlap TPR `~.82`,
clean-clique rate `~89%` (PROCEED).

Evidence: `results/generated/stage2d_composition/decision.json` records
4,000 raw rows, zero errors. Observed: `N=750` overlap TPR `.569`
(predicted `.59`), clean-clique rate `.287` (predicted `.26`) — REASSESS.
`N=1500` overlap TPR `.817` (predicted `.82`), clean-clique rate `.921`
(predicted `.89`) — PROCEED. Chain and fork TPR (`.815`-`.868` across
both `N`) behaved normally at both `N`, matching every prior charter. A
pooled average at `N=750` (`(.816+.815+.569)/3 = .733`) would also have
failed, but by a smaller, less diagnostic margin than the per-motif
breakdown gave. See `docs/stage2d_report.md` for the full breakdown.

Decision: The observed split matches the pre-specified prediction.
Extending `VALIDATED_CLIQUE_SIZES` to include size 5 is safe and correct
when the mechanism gets a chance to run (consistent with D-017), but for
this DGP's weak cross-branch signal, screening reliably provides that
chance only from `N=1500`, not `N=750`, despite `N=750` already being
comfortably above the DPI mechanism's own established floor (D-010/D-011).

Rationale: This is a genuinely new, narrower bottleneck, distinct from
every `N`-floor question characterized so far: it is a property of
*screening's* detection power for a specific weak-signal DGP shape, not
of the DPI conditioning mechanism (which D-017 already showed works
correctly whenever it runs) or of the general `N >= 700`-`750` floor
(D-010/D-011, which concerns DPI's own power, not screening's). That the
outcome matched pre-charter arithmetic closely is a successful
pre-specified prediction and evidence the bottleneck's *mechanism* was
understood well enough to anticipate its numeric size correctly — but
not independent confirmation, since the pre-charter check and the frozen
run share the same DGP and code assumptions rather than being derived
two separate ways (correction, second peer review, 2026-08-30).

Consequences: Trusting a validated clique size for a given DGP shape
should not be assumed safe at every `N` where the DPI mechanism itself is
validated — screening's detection power for that specific shape's signal
strength must be separately checked, as this charter did. This is not a
general statement that `VALIDATED_CLIQUE_SIZES = {3,4,5}` is unsafe (the
hub shape, D-016, worked fine at both tested `N`); it is specific to
weak-signal shapes like this one. `docs/validated_operating_ranges.md`
should record this as a distinct, DGP-dependent caveat rather than folding
it into the general `N`-floor entries.

## D-019: Bootstrap edge stability separates true from false edges; a known pruning failure shows partial, not complete, stability (R4)

Date: 2026-08-30

Stage: R4 / Stage 3

Status: PROCEED at both `N = 750` and `N = 1500` (primary DGP);
secondary DGP is diagnostic only, no PROCEED/REASSESS status

Decision timing: Predeclared gate evaluated after results, per
`docs/stage3_charter.md`

Question: Does bootstrap resampling of the composed screen-then-prune
pipeline produce a final-edge stability statistic (`pi_final`) that
meaningfully separates true edges from false ones under a calibrated
threshold — and does the outline's Section 17.5 predicted failure mode
("high bootstrap stability can occur for wrong edges") actually occur?

Prior specification: `docs/stage3_charter.md` froze a two-DGP design.
**Primary (gated)**: Stage 2b's disjoint chain/fork/triangle network
(already PROCEED at both `N`, D-014), `N = [750, 1500]`, 500-bootstrap
row resampling, 30 development + 30 validation outer replicates per
`N`. Per `N`, select the smallest `pi_min in {.70, .80, .90}` meeting,
on development, stability recall `>= .90`, pooled stability FDR
`<= .10`, and a stability-filtered final false-edge rate within `.01`
of the point-estimate baseline; the selected `pi_min` must meet the
same three criteria again on validation to PROCEED. **Secondary
(diagnostic only)**: Stage 2d's shared-node-overlap network at
`N = 750` — the specific condition D-018 found REASSESS on (overlap
indirect-edge pruning TPR `~.59`) — 30 replicates, no gate, reported
descriptively to answer Section 17.5 directly.

Evidence: `results/generated/stage3_bootstrap/decision.json`, 15,750
raw per-pair rows (12,600 primary + 3,150 secondary), zero errors,
runtime 333s. **Primary**: at both `N`, every candidate `pi_min`
(`.70`/`.80`/`.90`) was eligible on development; the smallest,
`pi_min = .70`, was selected and PROCEEDed on validation — `N=750`:
recall `.9952`, FDR `0`, stability-filtered final false-edge rate `0`
vs. baseline `.00069`; `N=1500`: recall `1.0`, FDR `0`, same `0` vs.
`.00069` comparison. **Secondary** (descriptive, `N=750`): mean
`pi_final` by category — `true_direct` `.99999`, `indirect_chain`
`.6338`, `indirect_fork` `.6345`, `indirect_overlap` `.5295`
(median `.545`), `null` `.0210`. See `docs/stage3_report.md`,
`stability_by_category.png`, and `secondary_overlap_diagnostic.png`.

Decision: **PROCEED for the primary DGP at both `N`.** Final-edge
bootstrap stability separates true direct edges (`pi_final ~1.0`) from
null pairs (`pi_final ~0.02`) almost completely, and the least
conservative eligible threshold (`pi_min = .70`) recovers essentially
every true edge while adding no measurable false-edge cost beyond the
point estimate's own baseline. **The secondary DGP's descriptive result
answers Section 17.5 directly, but only partially in the direction the
outline flagged as a risk**: D-018's known-mispruned `indirect_overlap`
edges do show elevated stability relative to null pairs (`.53` vs.
`.02`, roughly 25x) — confirming that a wrongly-retained edge is not
automatically unstable — but their stability is well below true edges'
(`.53` vs. `~1.0`) and even below the network's correctly-pruned chain
and fork indirect edges (`~.63`).

**Correction (2026-08-30, while chartering the follow-up):** the
preceding paragraph's `pi_min = .70` remark was based on the *pooled*
mean across both correctly-pruned and wrongly-retained instances of the
overlap-indirect edge type, which mixes two different populations and
is not the right statistic for a filter that only ever acts on edges
the point estimate already kept. Split by the point estimate's own
decision, the wrongly-retained instances are *more* stable (mean
`.737`, median `.745`, `n=60`) than the correctly-pruned ones (mean
`.322`, `n=60`) — so a `pi_min = .70` filter would remove only `40%` of
them, not "most." See `docs/stage3b_charter.md` for the corrected
conditional analysis and the higher threshold range (`pi_min in {.80,
.90, .95, .98}`) it motivates instead.

Rationale: The primary result is the charter's central question,
answered cleanly: bootstrap stability is not statistical noise here,
it is a genuinely separating statistic, at least for a composed
pipeline already known to work well (D-014). The secondary result is
more nuanced than the outline's Section 17.5 framing implies "high
stability for wrong edges" as a binary risk — here, wrongness produces
*intermediate*, not *high*, stability, still clearly distinguishable
from both extremes with enough resolution to matter. This is exactly
why Section 17.5 asks for this test explicitly rather than assuming
bootstrap either always helps or never does: the answer is graded, not
binary, and depends on how weak the underlying signal driving the
mispruning is (D-018 already established the overlap DGP's cross-branch
correlation is weak, `~.135`).

Consequences: Bootstrap edge stability is validated as a meaningfully
separating statistic for `p=15`, `N in [750, 1500]`, on a disjoint-triad
composed pipeline, at `B=500` row bootstraps — not validated for hub or
overlap-containing networks' own gate criteria, other resampling
schemes, or other `B` values. The secondary finding — that
wrongly-retained overlap edges are stability-separable from true edges,
at a materially higher threshold than the primary DGP's own `pi_min`
(see the 2026-08-30 correction above) — is a promising lead for a
future charter (does stability filtering, properly gated on the overlap
DGP itself, measurably improve topology quality there, per Section
17.6's second bullet?), not a claim that it already does; this is now
`docs/stage3b_charter.md`. Per this charter's explicit non-goals
section, `pi_final` must continue to be reported as a
resampling-reproducibility statistic, never as a p-value or confidence
level, in any report built on this evidence.

## D-020: Bootstrap stability filtering rescues the overlap DGP's N=750 failure (R4b)

Date: 2026-08-30

Stage: R4b / Stage 3

Status: PROCEED at both `N = 750` and `N = 1500`

Decision timing: Predeclared gate evaluated after results, per
`docs/stage3b_charter.md`

Question: Does a post-hoc bootstrap-stability filter (drop an edge from
the final graph if `pi_final < pi_min`, calibrated on the overlap DGP
itself) clear D-018's `.80` overlap indirect-edge TPR gate at `N=750`,
without wrongly removing true direct edges or regressing `N=1500`?

Prior specification: `docs/stage3b_charter.md` corrected D-019's pooled
`pi_final` framing (wrongly-retained overlap edges are, split by the
point estimate's own decision, *more* stable — mean `.737` — than the
pooled `.53` figure suggested) and predicted PROCEED at `N=750` with a
selected `pi_min` somewhere in `{.90, .95, .98}`. Candidate grid: `{.80,
.90, .95, .98}`. Gate per `N`: overlap indirect TPR `>= .80`, true-edge
FPR `<= .10`, chain/fork indirect TPR no worse than baseline
(safe-by-construction), final false-edge rate within `.01` of baseline
(also safe-by-construction) — select smallest eligible `pi_min` on
development (0-29), confirm on validation (30-59).

Evidence: `results/generated/stage3b_stability_filter/decision.json`,
12,600 raw rows, zero errors, runtime 689s. **`N=750`**: baseline
(unfiltered) overlap TPR `.633` (development) / `.558` (validation) —
below the `.80` gate, replicating D-018's failure on fresh evidence.
Every candidate `pi_min` was eligible on development; the smallest,
`pi_min=.80`, was selected and cleared validation: overlap TPR
`.867`, true-edge FPR `0`, chain TPR `.867`, fork TPR `.933`, final
false-edge rate `0`. **`N=1500`**: baseline overlap TPR `.692`
(development) / `.808` (validation) — the development-partition dip
below `.80` is 60-replicate sampling noise (D-018's original,
2000-replicate estimate was `.817`; this run's own validation partition
recovers `.808`, consistent with D-018), not a new finding that `N=1500`
newly fails without filtering. `pi_min=.80` selected and validated:
overlap TPR `.883`, true-edge FPR `0`. See `docs/stage3b_report.md`,
`overlap_tpr_vs_pi_min.png`, `before_after_filtering.png`.

Decision: **Stability filtering rescues `N=750`.** The smallest
candidate threshold, `pi_min=.80`, was sufficient — lower than the
`{.90, .95, .98}` range the pre-charter conditional analysis predicted,
meaning the true separation between wrongly-retained overlap edges and
true edges is *cleaner* at full statistical resolution (60 replicates,
formally gated) than the 30-replicate exploratory slice suggested. True
direct edges were never wrongly removed at any tested `pi_min`, at
either `N` — true-edge FPR was exactly `0` throughout, matching the
pre-charter check's `0%`-cost observation exactly, now on independent,
gated evidence.

Rationale: This is the first charter in this project to demonstrate a
genuine *repair* of a previously identified failure mode without
collecting more data, not merely a validation or invalidation of an
existing mechanism (contrast with every prior R-series charter). The
repair works because the two conditions this DGP creates are
distinguishable in a way pure point estimation cannot see but resampling
can: an edge the point estimate barely, contingently kept (because this
replicate's specific draw happened to push a weak `~.135` correlation's
p-value under `alpha` for 4 simultaneous cross-branch pairs) tends to
*not* survive most of that same replicate's own bootstrap resamples as
reliably as a genuinely strong edge does — even though, per the D-019
correction, it survives more resamples than a purely null edge would.
The gap between "survives most resamples" (true edges, `~1.0`) and
"survives about three-quarters" (wrongly-kept overlap edges, mean
`.737`) turned out to be wide enough for a `pi_min=.80` cut to fall
cleanly between them on real gated evidence, even though the
exploratory pre-check's own numbers suggested needing to go higher.

Consequences: Bootstrap stability filtering, calibrated at `pi_min=.80`
via `B=500` row bootstraps, is validated as a rescue mechanism
specifically for the shared-node-overlap DGP (`p=15`, `N in [750,
1500]`, `~.135` cross-branch correlation). This does **not** validate:
stability filtering for other under-powered shapes, weaker or stronger
signals, other `B` values, or a `pi_min` outside `{.80, .90, .95, .98}`
— a finer grid below `.80` was never tested, so whether an even lower,
cheaper-to-satisfy threshold would also work is unknown. It does **not**
authorize adding a stability-filter stage to `mintnet.pipeline.compose`
as a production default — that is a separate architecture decision, and
the `B=500` bootstrap cost (roughly 500x the base pipeline's per-dataset
cost) is a real, unresolved practical concern for that future decision,
not resolved by this charter's PROCEED. `docs/validated_operating_ranges.md`
should record this as a distinct rescue-mechanism entry, not folded into
the existing overlap-DGP caveat (D-017/D-018), since it changes what is
achievable at `N=750` for this shape when filtering is applied, without
changing the underlying `N=750` screening-power limitation itself.

## D-021: Bootstrap stability's general selection gate transfers to the hub network (R4c)

Date: 2026-08-30

Stage: R4c / Stage 3

Status: PROCEED at both `N = 750` and `N = 1500`

Decision timing: Predeclared gate evaluated after results, per
`docs/stage3c_charter.md`

Question: Does Stage 3's general bootstrap-stability separation/
selection gate (recall `>= .90`, pooled FDR `<= .10`, no false-edge
regression, `pi_min in {.70, .80, .90}`) transfer, unmodified, to a
structurally different composed-pipeline DGP — the chain/fork/hub
network (D-016) — or was Stage 3's PROCEED specific to the
disjoint-triad shape it was tested on?

Prior specification: `docs/stage3c_charter.md` re-ran Stage 3's exact
primary-DGP procedure on Stage 2c's DGP instead of Stage 2b's, with no
new criteria or grid — explicitly *not* chasing a known failure (unlike
Stage 3b), since D-016 already PROCEEDs cleanly at the point estimate
(`.820`-`.853` indirect TPR, `.000` true-edge FPR at both `N`). The
predeclared expectation was a clean PROCEED, stated as something to
confirm rather than assume.

Evidence: `results/generated/stage3c_hub_stability/decision.json`,
12,600 raw rows, zero errors, runtime 758s. Every candidate `pi_min`
was eligible on development at both `N`; the smallest, `pi_min=.70`,
was selected and PROCEEDed on validation at both — `N=750`: recall
`1.0`, FDR `0`, final false-edge rate `0` vs. baseline `0`; `N=1500`:
recall `1.0`, FDR `0`, final false-edge rate `0` vs. baseline `.0007`.
Development-stage FDR at `N=750` for the two lower thresholds
(`pi_min=.70`: `.0073`; `pi_min=.80`: `.0041`) was nonzero but still
comfortably under the `.10` gate — the only nonzero FDR values recorded
across this charter's entire evidence, and still an order of magnitude
below the bar. See `docs/stage3c_report.md`,
`stability_by_category.png`.

Decision: **The general stability-selection gate transfers cleanly to
the hub shape**, exactly as predicted, at the same `pi_min=.70` that
was selected on the disjoint-triad DGP in Stage 3. No new threshold
range, no rescue needed, no surprises — this is a confirmation, not a
repair (contrast with D-020).

Rationale: Unlike the overlap DGP (D-018's known weak-signal failure,
which needed Stage 3b's higher, DGP-specific `pi_min` range), the hub
shape's signal is strong enough at the point estimate that bootstrap
resampling reproduces the same clean separation Stage 3 found on the
disjoint-triad DGP, with no adjustment. This is the useful negative
result the charter set out to get: confirmation that Stage 3's original
finding was not an artifact of the specific disjoint-triad shape it
happened to be tested on, without having to assume that from a single
data point.

Consequences: Bootstrap edge stability's general recall/FDR/
no-regression gate is now validated on two structurally different
composed-pipeline DGPs (disjoint-triad, D-019; hub, D-021) at `p=15`,
`N in [750, 1500]`, `B=500`, both selecting `pi_min=.70`. It remains
**not** validated as this kind of general gate on the shared-node-
overlap DGP (Stage 3b addressed that DGP only through a narrower,
filtering-specific lens with a different threshold range) — whether the
general gate itself, run unmodified on the overlap DGP the way this
charter ran it on the hub DGP, would also transfer or would instead
reproduce D-019's more nuanced intermediate-stability finding remains
an open, untested question. `docs/validated_operating_ranges.md` should
extend the Stage 3 bootstrap-stability row to note the hub-shape
confirmation, rather than adding a new row, since the validated range
and selected `pi_min` are unchanged from Stage 3 — only the tested shape
is new.
