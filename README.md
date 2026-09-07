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
from gopcnet import fit_gopc

adjacency = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)
```

`fit_gopc` (growing-order GOPC) is the recommended default pipeline
(see `docs/decision_log.md`'s D-053): it closes most of GOPC's
precision gap with a PC-algorithm skeleton comparator on the composed
networks this repo's own Stage 5 benchmarks test, with zero measured
recall cost. `docs/decision_log.md` and `docs/validated_operating_ranges.md`
track this repo's own mechanism-by-mechanism validation history in
full.

A second variant, `fit_gopc_fixed_order`, is also available with the
same call signature -- closer in spirit to LOPC (Zuo et al., 2014), and
generally dominated by `fit_gopc` on this repo's own benchmarks, but
kept available for direct comparison:

```python
from gopcnet import fit_gopc_fixed_order

adjacency = fit_gopc_fixed_order(data, screening_alpha=0.001, dpi_alpha=0.01)
```

Both variants require continuous, approximately Gaussian data --
ordinal/categorical psychometric data is out of scope and has not been
validated. See each function's own docstring for full parameter and
return-value documentation, and `CHANGELOG.md` for release history.

Two comparator methods used throughout this project's own benchmarks
are also available, for benchmarking GOPC against them on your own
data: `fit_ebicglasso` (graphical lasso, EBIC-selected penalty) and
`fit_pc_skeleton` (the PC algorithm's skeleton phase only, no
orientation). Both return a small result object rather than a bare
array -- `result.adjacency`, not `result` itself:

```python
from gopcnet import fit_ebicglasso, fit_pc_skeleton

ebic_result = fit_ebicglasso(data)
pc_result = fit_pc_skeleton(data, alpha=0.01)
```

## What's in the package

`pip install`ing this package gives you `gopcnet.pipeline` (the two
`fit_gopc*` functions), `gopcnet.comparators` (`fit_ebicglasso`,
`fit_pc_skeleton`), and the `gopcnet.screening`, `gopcnet.dpi`, and
`gopcnet.mi` modules they're built from. It does **not** include
`gopcnet.experiments`, `gopcnet.simulation`, or `gopcnet.bootstrap` --
this repository's own internal scaffolding for running and validating
the Stage 1-5h benchmarks behind `docs/decision_log.md`. That code is
still in this repository and still tested; it's simply not part of
what an installed copy of the package ships. If you want to reproduce
or extend those benchmarks, work from a checkout of this repository
rather than an installed `gopcnet`.

## A note on the package name

This package was briefly named `mintnet` (inherited from the repository
this project was spun off from, `docs/spinoff_lopc_psychometrics_plan.md`),
before being renamed to `gopcnet` to match what it actually is. Charters
and decision-log entries written before the rename (`docs/decision_log.md`,
`docs/stage*_charter.md`) are frozen historical record and were not
retroactively edited -- where they reference `mintnet.*` module paths or
the method as "MINT," that reflects the name at the time of writing, not
a typo. The current, correct import path is `gopcnet.*` throughout.
