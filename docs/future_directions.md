# Future Directions (not chartered, not scheduled)

Ideas raised and deliberately deferred, recorded here so they don't get
lost rather than acted on. Nothing in this file is authorized work.

## Hybrid GOPC + PC method

Raised originally during the R6 comparator work (before the MI-boundary
discussion and the mi-native/GOPC split): *"should we actually find a
way to integrate PC into MINT's architecture as a supplemental
double-check where we know [the pruning mechanism] alone may begin to
falter?"* Never chartered.

This is a different kind of contribution than Stage 5g's growing-subset
port: not a refinement of GOPC's own mechanism using its own primitive,
but an actual combination of two different algorithms — e.g. running
both and taking their agreement, or using PC as a tie-breaker on GOPC's
own ambiguous/borderline edges, or vice versa.

**Deliberately sequenced after Stage 5g**, not run in parallel by
default: Stage 5g's own gap-closure result is informative for whether
this is worth doing at all.
- If Stage 5g reaches MATERIAL closure, a hybrid adds complexity for
  little remaining gain — the honest story becomes "an internal fix
  made GOPC precision-competitive with PC," and a hybrid would need its
  own separate justification.
- If Stage 5g reaches NO or only PARTIAL closure, that is the
  motivating evidence a hybrid paper would want to open with: "the
  obvious internal fix does not fully explain the gap; here is what
  combining with PC buys you instead."

**Open design questions, not yet resolved, if this is pursued:**
- Combination rule: union (either method flags an edge), intersection
  (both must agree), or an asymmetric rule (PC adjudicates only GOPC's
  own borderline/near-threshold edges)?
- Whether "combining two existing structure-learning methods" has its
  own prior art in the psychometric-network or general graphical-model
  literature — not checked yet; would need its own literature pass
  before claiming any novelty, exactly as `docs/spinoff_lopc_psychometrics_plan.md`
  did for GOPC's own base method.
- Whether this is still a "narrow, honest contribution" in the spirit
  established for this repo (see `docs/spinoff_lopc_psychometrics_plan.md`'s
  own framing discussion), or whether an ensemble method reopens the
  "novel algorithm" ambition this project has deliberately avoided.
