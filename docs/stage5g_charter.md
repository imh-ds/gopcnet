# Stage 5g Charter: Growing-Subset DPI vs. PC Skeleton — Testing Whether D-052's Diagnosed Fix Closes the Precision Gap

Status: **FROZEN before results**
Date: 2026-09-05

## Background and objective

D-051 found PC's skeleton beats GOPC's own precision on every tested
composed network, while missing weak true edges GOPC and EBICglasso
both catch. D-052 diagnosed a concrete, partial explanation: a real
share of GOPC's residual false positives are `passthrough_unconditioned`
edges — ones whose connected component was never a validated 3/4/5-node
clique, so DPI never actually tested them at all. That charter's own
"Consequences" section named the candidate fix explicitly ("extending
DPI's own conditioning to examine non-clique or smaller components")
but did not attempt it, since a real algorithm change needs its own
fresh validation, not an assumption that it plausibly helps.

A growing-conditioning-set variant of exactly this kind was later built
and validated on a different codebase (mintnet's `mi-native` branch,
D-053) for an unrelated purpose (scoping how much conditioning depth a
future MI estimator would need) — but it was built and tested using
*only* the already-validated Fisher-z partial-correlation primitive, no
MI involved. It is architecturally exactly the fix D-052 named: instead
of requiring a full validated clique, it tests every connected
component's own growing conditioning subsets (size 1, 2, ... up to a
cap), pruning as soon as any subset fails to reject independence. This
charter ports that code unchanged (`mintnet.pipeline.growing_subset_dpi`)
into this repo and tests, for the first time, whether it actually closes
GOPC's own diagnosed gap with PC — not assumed from D-053's own
different validation context.

## Design

**Paired, not fresh, reference data.** Reuses D-047's own GOPC
(`method="mint"` in the archived evidence) and D-051's own PC
(`method="pc"`) rows exactly as archived in
`evidence/stage5_benchmarks/stage5a_comparator_benchmark/raw_metrics.csv`
and `evidence/stage5_benchmarks/stage5e_pc_skeleton/raw_metrics.csv` —
not rerun. Both were computed on data drawn from the identical
`(dgp, N, replicate)` seed as this charter's own new run (all three
share `stage5a`'s own `_condition_seed`, `master_seed=20260830`,
`strength=0.5`), so this is a three-way paired comparison on identical
draws, not three separately-drawn benchmarks.

**New run**: growing-subset DPI
(`mintnet.pipeline.growing_subset_dpi.growing_subset_dpi`) on GOPC's
own screened candidate graph
(`compute_pairwise_screening_evidence` + `screen_uncorrected`,
`screening_alpha=0.001`, unchanged from D-047), replacing only the
pruning step (`compose_screen_then_prune` to `growing_subset_dpi`),
`dpi_alpha` from D-012's own general `alpha(N)` formula (unchanged from
D-047/D-051 — same fair-comparison rule Stage 5a/5e already used),
`max_conditioning_size=4` (D-053's own validated default, not
re-tuned here).

Full grid, unchanged from D-047/D-051: all five DGP shapes
(`chain_fork_hub`, `overlap`, `triangle_balanced`, `triangle_moderate`,
`triangle_strong`), `N = [400, 500, 600, 750, 1000, 1500, 1750]`, `2000`
replicates (development `0`-`999`, validation `1000`-`1999`).

## Selection and gate

Computed per `(dgp, N)` cell on validation replicates only, mirroring
Stage 5a/5e's own convention:

1. **Recall must not regress materially**: growing-subset's own recall
   within `0.02` absolute of GOPC-original's own recall, at every
   tested `(dgp, N)`. This is the charter's own primary gate — D-053's
   "zero recall cost" finding was established in a different context
   (isolated/composed motifs under Stage 6a's own design, not this
   exact grid), so it is re-checked here, not assumed to transfer.
2. **Gap-closure classification**, per cell where PC's own precision
   exceeds GOPC-original's own precision (the cells D-051 identified as
   the actual gap):
   `closure = (growing_subset_precision - original_precision) / (pc_precision - original_precision)`.
   - **MATERIAL closure**: `closure >= 0.5` at a majority of the 7
     tested `N` for a given shape.
   - **PARTIAL closure**: `0 < closure < 0.5` at a majority of `N`.
   - **NO closure**: `closure <= 0` at a majority of `N` (growing-subset
     does not improve precision over the original, or makes it worse).

**PROCEED to a paper-ready comparison** if recall holds (gate 1) and at
least PARTIAL closure is observed on both composed shapes
(`chain_fork_hub`, `overlap` — the two D-051/D-052 actually diagnosed).
**REASSESS** if recall regresses materially anywhere, regardless of any
precision gain (an edge gained by systematically dropping other edges
is not the fix this charter is testing).

No result is assumed. MATERIAL closure would mean the internal fix
essentially resolves the PC comparison and a hybrid method may not be
worth pursuing; NO closure on both shapes would mean the diagnosed
mechanism was not the (or not the only) real driver of the gap, and
motivates the hybrid-method idea (see `docs/future_directions.md`)
instead.

## Explicit non-goals

- **No re-tuning of `max_conditioning_size`, `screening_alpha`, or
  `dpi_alpha`.** Uses D-053's and D-047's own already-validated values
  unchanged — isolating the one variable this charter actually tests
  (the pruning mechanism itself).
- **No hybrid GOPC/PC method.** That is a distinct, separately-scoped
  future idea (see `docs/future_directions.md`), deliberately not
  attempted here regardless of this charter's own outcome.
- **No orientation phase, no new DGP.** Same boundary as every prior
  Stage 5 charter.

## Required evidence

Resolved configuration, this charter's SHA-256, commit and runtime
metadata, raw per-replicate evidence for the new growing-subset run,
the merged three-way comparison table (referencing D-047's and D-051's
own archived rows, not recomputing them), gap-closure classification
per shape, decision, report.
