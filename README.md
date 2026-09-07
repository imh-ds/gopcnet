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

result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)
result.adjacency  # (p, p) boolean, symmetric
result.weights    # (p, p) signed partial correlations, zero where adjacency is False
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

result = fit_gopc_fixed_order(data, screening_alpha=0.001, dpi_alpha=0.01)
```

Both variants require continuous, approximately Gaussian data --
ordinal/categorical psychometric data is out of scope and has not been
validated. See each function's own docstring for full parameter and
return-value documentation, and `CHANGELOG.md` for release history.

**Edge weights.** `.weights` is a signed partial-correlation matrix,
but what "partial correlation" means for a given edge depends on which
variant produced it and whether that edge was ever conditioning-tested
at all -- see `docs/decision_log.md`'s D-055 for the exact convention
and why it was chosen (in short: the single deciding test's own value
for fixed-order GOPC; the weakest of every subset an edge had to
survive for growing-order GOPC; the raw marginal correlation for any
edge no conditioning test ever ran on). This is a derived diagnostic
quantity, not a separately benchmarked one -- only the boolean
adjacency's precision/recall has been validated.

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

## Bootstrap edge stability

`bootstrap_edge_stability` runs a nonparametric row bootstrap through
any one of the four fit functions above and reports, per pair, how
often it was retained as an edge across resamples -- and, for the two
`fit_gopc*` functions, the mean/std of its edge weight across those
same resamples. Bind a method's own hyperparameters with
`functools.partial` first, since this function doesn't know about them:

```python
from functools import partial
import numpy as np
from gopcnet import fit_gopc, bootstrap_edge_stability

fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
stability = bootstrap_edge_stability(data, fit, bootstraps=1000, rng=np.random.default_rng(0))

stability.inclusion_probability  # (p, p): fraction of resamples each pair was an edge
stability.weight_mean            # (p, p) or None -- None for fit_ebicglasso/fit_pc_skeleton,
stability.weight_std             #   which don't define an edge weight at all (D-055)
```

A resample on which the fit raises (a degenerate, near-zero-variance
draw) is excluded from both the numerator and denominator rather than
counted as edge-absent; `stability.failed_bootstraps` records how many.

This works with `fit_ebicglasso` and `fit_pc_skeleton` directly too
(no `functools.partial` needed unless you want non-default
hyperparameters, since every one of their parameters already has a
default).

## Centrality

`compute_centrality` takes any weight matrix of the shape `fit_gopc`,
`fit_gopc_fixed_order`, and `bootstrap_edge_stability` already produce
(signed, symmetric, zero diagonal) and reports four standard node
centrality measures:

```python
from gopcnet import compute_centrality

centrality = compute_centrality(result.weights)
centrality.strength            # sum of |weight| per node
centrality.expected_influence  # signed sum of weight per node (Robinaugh et al., 2016)
centrality.closeness           # 1 / (sum of shortest-path distances to every reachable node)
centrality.betweenness         # fraction of others' shortest paths passing through this node
```

`closeness` and `betweenness` both need a *distance*, not a weight,
per edge; following the qgraph/bootnet convention, distance is
`1 / |weight|` -- a stronger association, positive or negative, is a
shorter, more direct connection, so sign affects `expected_influence`
but not the two path-based measures. An isolated node (no path to any
other node) gets `0.0` for both, not an error. Each measure is also
available on its own (`strength`, `expected_influence`,
`closeness_centrality`, `betweenness_centrality`) if you don't need
all four. Not GOPC-specific -- any weighted adjacency matrix of this
shape works.

## What's in the package

`pip install`ing this package gives you `gopcnet.pipeline` (the two
`fit_gopc*` functions), `gopcnet.comparators` (`fit_ebicglasso`,
`fit_pc_skeleton`), `gopcnet.stability` (`bootstrap_edge_stability`),
`gopcnet.metrics` (`compute_centrality`), and the `gopcnet.screening`,
`gopcnet.dpi`, and `gopcnet.mi` modules they're built from. It does
**not** include `gopcnet.experiments`,
`gopcnet.simulation`, or `gopcnet.bootstrap` -- this repository's own
internal scaffolding for running and validating the Stage 1-5h
benchmarks behind `docs/decision_log.md` (`gopcnet.bootstrap` is an
older, narrower bootstrap tool specific to one internal pipeline
variant -- not the generic `gopcnet.stability.bootstrap_edge_stability`
described above, which is a separate, newer, fully public module).
That code is still in this repository and still tested; it's simply
not part of what an installed copy of the package ships. If you want
to reproduce or extend those benchmarks, work from a checkout of this
repository rather than an installed `gopcnet`.

## A note on the package name

This package was briefly named `mintnet` (inherited from the repository
this project was spun off from, `docs/spinoff_lopc_psychometrics_plan.md`),
before being renamed to `gopcnet` to match what it actually is. Charters
and decision-log entries written before the rename (`docs/decision_log.md`,
`docs/stage*_charter.md`) are frozen historical record and were not
retroactively edited -- where they reference `mintnet.*` module paths or
the method as "MINT," that reflects the name at the time of writing, not
a typo. The current, correct import path is `gopcnet.*` throughout.
