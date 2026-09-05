# gopcnet
Growing-Order Partial Correlation (GOPC) Network

Screens pairwise associations by Fisher-z correlation, then prunes
indirect edges with a growing-conditioning-set conditional-independence
test motivated by the data-processing-inequality logic behind
ARACNE-style pruning (see `docs/spinoff_lopc_psychometrics_plan.md` for
the full framing and its relationship to LOPC, systems biology's own
closely related method).

## Usage

```python
from mintnet.pipeline import fit_gopc

adjacency = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)
```

`fit_gopc` is the recommended default pipeline (see `docs/decision_log.md`'s
D-053): it closes most of GOPC's precision gap with a PC-algorithm
skeleton comparator on the composed networks this repo's own Stage 5
benchmarks test, with zero measured recall cost. `docs/decision_log.md`
and `docs/validated_operating_ranges.md` track this repo's own
mechanism-by-mechanism validation history in full.
