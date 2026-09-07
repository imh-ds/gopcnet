# gopcnet
Growing-Order Partial Correlation (GOPC) Network

Screens pairwise associations by Fisher-z correlation, then prunes
indirect edges with a growing-conditioning-set conditional-independence
test motivated by the data-processing-inequality logic behind
ARACNE-style pruning (see `docs/spinoff_lopc_psychometrics_plan.md` for
the full framing and its relationship to LOPC, systems biology's own
closely related method).

## Installation

```bash
pip install git+https://github.com/imh-ds/gopcnet.git
```

Not yet published to PyPI -- install directly from this repository.

## Usage

```python
from gopcnet.pipeline import fit_gopc

adjacency = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)
```

`fit_gopc` is the recommended default pipeline (see `docs/decision_log.md`'s
D-053): it closes most of GOPC's precision gap with a PC-algorithm
skeleton comparator on the composed networks this repo's own Stage 5
benchmarks test, with zero measured recall cost. `docs/decision_log.md`
and `docs/validated_operating_ranges.md` track this repo's own
mechanism-by-mechanism validation history in full.

## A note on the package name

This package was briefly named `mintnet` (inherited from the repository
this project was spun off from, `docs/spinoff_lopc_psychometrics_plan.md`),
before being renamed to `gopcnet` to match what it actually is. Charters
and decision-log entries written before the rename (`docs/decision_log.md`,
`docs/stage*_charter.md`) are frozen historical record and were not
retroactively edited -- where they reference `mintnet.*` module paths or
the method as "MINT," that reflects the name at the time of writing, not
a typo. The current, correct import path is `gopcnet.*` throughout.
