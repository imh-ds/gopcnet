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
Exploratory (non-gating) calibration of the confidence score `1 - p_value`
against ground truth gives a pooled Brier score of `.081` (naive-baseline
`.25`), improving with `N`.

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
reasonable next step given the trend evidence. Separately, the calibration
result is promising enough to be worth a dedicated future charter for a
confidence-scored edge representation, per `docs/stage1b_charter.md`'s
consequences section; this remains an executive decision, not an automatic
next step.
