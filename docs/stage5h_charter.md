# Stage 5h Charter: Signal-Strength Sweep, Four-Way — Extending D-050 to PC and Growing-Order GOPC, on the Manuscript's Own Validated N Grid

Status: **FROZEN before results**
Date: 2026-09-06

## Background and objective

D-050 (Stage 5d) found that GOPC-original's precision advantage over
EBICglasso on the `overlap` network grows with true signal strength,
where EBICglasso's own precision collapses — but that charter compared
only two methods (`mint`, `ebicglasso`), and its own `N` grid
(`{500, 1500}`) included a value, `N=500`, later found to fall outside
GOPC's own pruning significance level's validated range (D-011;
`docs/validated_operating_ranges.md`'s own "interpolation only, `N` in
`[700, 3000]`" scope statement). The manuscript currently being drafted
from this project's evidence (`manuscript/paper.qmd`) therefore reports
D-050's own finding at a single validated sample size, `N=1500`, and
only for the two methods D-050 originally tested — while every other
result in that manuscript (D-047, D-051, D-053) is a four-way comparison
(EBICglasso, PC, GOPC fixed-order, GOPC growing-order) across four
validated sample sizes (`{750, 1000, 1500, 1750}`). This charter closes
both gaps in one run rather than two, per the tradeoff already discussed
with the user: doing so now is cheap, since PC's skeleton fit
(`mintnet.comparators.pc_skeleton.fit_pc_skeleton`) and growing-order
GOPC (`mintnet.pipeline.gopc.fit_gopc`) are both already implemented and
separately validated (D-051, D-053) — this charter applies them to a new
manipulation (signal strength), not new methodology.

**What this charter is not**: not a re-litigation of D-050's own
finding, which stands as reported for its own original scope (two
methods, `N in {500, 1500}`). Not a new algorithm or a new DGP. Not a
retroactive edit of `evidence/stage5_benchmarks/stage5d_strength_sweep/`,
which remains archived and cited exactly as it is.

## Design

**Full four-way comparison**: `ebicglasso`, `pc`, `mint` (GOPC
fixed-order, `mintnet.pipeline.compose.compose_screen_then_prune`), and
`gopc_growing_subset` (GOPC growing-order, `mintnet.pipeline.gopc.fit_gopc`),
fit on identical data at every replicate — a four-way paired design,
mirroring D-053's own paired approach.

**DGP shapes**: `chain_fork_hub` and `overlap`, the same two shapes
D-050 used (the only two shapes this manipulation's own signal-strength
parameterization applies to in the existing DGP registry — the three
triangle shapes have their own fixed asymmetry profiles, not a
continuously variable strength parameter, and are out of scope here as
they were for D-050).

**Sample sizes**: `N = [750, 1000, 1500, 1750]` — the manuscript's own
full validated grid (Section 4.3's own stated scope restriction),
replacing D-050's `{500, 1500}` rather than extending it, since `N=500`
is exactly the value the restriction excludes. This is a deliberate
departure from D-050's own grid, not an oversight: preserving `N=500`
would just reproduce the same excluded-evidence problem this charter
exists to close.

**Signal strength**: `strength in {.3, .5, .7}`, unchanged from D-050 —
the same three levels, same units, same DGP strength parameter.

**Noise**: held at each shape's own native column count (multiplier
`1`), unchanged from D-050 — the noise-count axis is characterized
separately (D-048/D-049) and is not this charter's own variable.

**Configuration, held fixed and unchanged from the charters that
validated each method**:
- EBICglasso: `gamma=.5`, `n_lambda=100`, `lambda_min_ratio=.01`
  (D-047's own values, unchanged).
- GOPC fixed-order and growing-order: `screening_alpha` via Stage 5c's
  `alpha(p)` interpolation (D-049's own preferred configuration, the
  same one D-050 itself already used), `dpi_alpha` via D-012's general
  `alpha(N)` formula (unchanged from every prior R6/Stage 5 charter),
  growing-order's `max_conditioning_size=4` (D-053's own validated
  default, not re-tuned here).
- PC: `pc_alpha=0.01` (D-051's own fixed, N-independent value,
  unchanged).

**Seeding**: a new, disjoint stage tag (not `504`, D-050's own tag, and
not `501`/`505` used by Stage 5a/5g), following this project's own
`_condition_seed(master_seed, stage_tag, dgp_index, sample_index,
strength_index, replicate)` convention. This is a fresh, self-contained
seed stream, not a reuse of D-050's own archived draws: D-050's sample
sizes (`{500, 1500}`) and this charter's (`{750, 1000, 1500, 1750}`)
assign different positional indices to `N=1500` (index `1` vs. index
`2`), so reusing D-050's own tag with an expanded sample-size list would
silently change what data `N=1500` draws — a seed-derivation pitfall
worth naming explicitly so it is not hit by accident. `master_seed`
unchanged (`20260830`, this project's own standing convention).
`2,000` replicates per cell (development `0`-`999`, validation
`1000`-`1999`).

## Sharding

Shard by `(dgp, N, strength)`, mirroring Stage 5d's own three-dimension
sharding; `.github/workflows/sharded_benchmark.yml`'s existing
three-dimension support requires no changes.

## Decision structure

**Descriptive, not a gate** — same standing as D-050 itself. This
charter is not testing a falsifiable mechanistic claim about a new
method; it is extending an existing, already-reported descriptive
finding to more methods and more sample sizes, on grounds of
completeness and internal consistency with the rest of the manuscript's
own evidence base.

**Predeclared reporting requirements**, all mandatory regardless of
outcome:

1. For each `(dgp, method)` pair, state whether precision is
   increasing, decreasing, flat, or non-monotonic across ascending
   strength, at every one of the four sample sizes — not collapsed into
   a single summary across `N`.
2. **Recall reported explicitly and prominently for every method at
   every cell**, not folded into F1. This matters more here than it did
   for D-050's original two-method design: PC is already known (D-051,
   and the manuscript's own `triangle_strong` result) to have a real
   recall deficit relative to EBICglasso and both GOPC variants under
   some conditions. Whether that deficit appears, disappears, or
   changes with signal strength on `chain_fork_hub`/`overlap`
   specifically is new information this charter is positioned to catch,
   not an assumption carried over from the triangle-motif result.
3. Report whether D-050's own original finding (EBICglasso's precision
   collapses with strength on `overlap` at `N=1500`, GOPC-original's
   stays flat) replicates under this charter's own fresh draw at the
   same `N` and strength values — since this is a new seed stream, not
   a re-score of D-050's own data, this is a genuine replication check,
   not a formality.

## Explicit non-goals

- **No re-tuning of any method's own configuration.** Every value above
  is carried forward unchanged from the charter that originally
  validated it (D-047, D-049, D-051, D-053) — this charter tests
  behavior under a new manipulation, not new configurations.
- **No hybrid GOPC/PC method, no hybrid design work.** Unrelated to this
  charter's own scope (`docs/future_directions.md`).
- **No modification of `evidence/stage5_benchmarks/stage5d_strength_sweep/`.**
  D-050's own archived evidence is left exactly as it is; this charter's
  own results are archived separately.
- **No claim that this charter's own `N=1500` results are numerically
  identical to D-050's own `N=1500` results.** They are drawn from a
  different seed stream (see Seeding above) and are expected to differ
  in the third or fourth decimal place while telling the same
  qualitative story, not to reproduce D-050's own rows exactly.

## Required evidence

Resolved configuration, this charter's SHA-256, commit and runtime
metadata, raw per-replicate metrics for all four methods at every
`(dgp, N, strength)` cell (`2 shapes x 4 N x 3 strengths x 4 methods`,
full grid, no cell omitted regardless of outcome), a report presenting
the reporting requirements above, and the replication check against
D-050 stated explicitly as its own section.

## Consequences

If the descriptive pattern holds as D-050 originally found (EBICglasso
declining, GOPC-original flat) and PC/growing-order GOPC's own patterns
are informative alongside it, this charter's own archived evidence
becomes the manuscript's own source for its signal-strength figure and
table, superseding D-050 as the manuscript's own primary citation for
that specific claim — while D-050 itself remains valid, archived, and
cited in this project's own decision log as the original, narrower
finding it always was. If PC or growing-order GOPC show an unexpected
recall or precision pattern under this manipulation, that is new
evidence to report as found, not a failure condition for this charter
(there is no gate to fail, per the Decision structure above) — and
would be exactly the kind of finding worth its own follow-up if
material.
