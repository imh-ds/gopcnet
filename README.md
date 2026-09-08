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

## Correlation-stability (CS) coefficient

A different reliability question from edge stability above: how much
of your sample could you lose before a statistic (usually a centrality
measure) stops resembling the full-sample estimate at all? This is
`bootnet`'s own signature diagnostic (Epskamp, Borsboom, & Fried, 2018)
-- the number published network psychometrics papers report to argue
whether a network's centrality is even worth interpreting
(`CS(cor = 0.7) = 0.52`, meaning up to 52% of cases could be dropped
before centrality stops correlating with the full sample at 0.7 or
better, in 95% of resamples).

```python
from functools import partial
import numpy as np
from gopcnet import fit_gopc, strength, case_drop_bootstrap, cs_coefficient

fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
case_drop = case_drop_bootstrap(
    data, fit, lambda r: strength(r.weights),
    bootstraps_per_proportion=1000, rng=np.random.default_rng(0),
)
result = cs_coefficient(case_drop)
result.cs_coefficient                       # e.g. 0.4 -- up to 40% droppable
result.pass_rate_by_proportion_retained      # per-level detail, not just the summary number
```

`case_drop_bootstrap` subsamples *without* replacement at shrinking
sample sizes (unlike `bootstrap_edge_stability`, which resamples *with*
replacement at the full size) -- pass any statistic function
(`lambda r: strength(r.weights)`, `lambda r: r.weights[np.triu_indices_from(r.weights, k=1)]`
for raw edge weights, or your own), and it works with any of the four
fit functions, not just `fit_gopc`. `cs_coefficient` reduces that
output to the coefficient, using Spearman correlation and the
literature's own `0.7`/`0.95` thresholds by default (both overridable)
-- see `docs/decision_log.md`'s D-056 for the exact convention,
including the monotonic pass-rate rule and how an undefined (NaN)
correlation is handled.

## Bootstrap difference testing

Is one specific edge (or one node's centrality) really different from
another, or is that within bootstrap noise? Neither tool above answers
this: `bootstrap_edge_stability` only keeps aggregates (mean/std),
which can't build a CI on a *difference* between two specific entries
without wrongly treating them as independent.

```python
from functools import partial
import numpy as np
from gopcnet import fit_gopc, strength, bootstrap_replicates, difference_test

fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
replicates = bootstrap_replicates(
    data, fit, lambda r: strength(r.weights), bootstraps=1000, rng=np.random.default_rng(0),
)
result = difference_test(replicates, index_a=0, index_b=1)  # node 0's strength vs node 1's
result.difference     # full-sample point estimate: strength[0] - strength[1]
result.ci_low, result.ci_high  # 95% paired percentile bootstrap CI on that difference
result.significant    # True iff the CI excludes zero
```

`bootstrap_replicates` runs the same nonparametric bootstrap
`bootstrap_edge_stability` does, but keeps every replicate's raw
statistic vector instead of aggregating -- pass any statistic function,
same as `case_drop_bootstrap`. The CI is built from each replicate's
own `statistic_a - statistic_b` (both computed from the same resampled
draw), not from independently-combined means/stds -- see
`docs/decision_log.md`'s D-057 for why that distinction matters.

`threshold_by_inclusion_probability` is a smaller, separate
convenience: turn `EdgeStabilityResult.inclusion_probability` directly
into a "safe" adjacency matrix (only edges above some inclusion
frequency survive), matching the idea behind `bootnet`'s own
`bootInclude()`:

```python
from gopcnet import threshold_by_inclusion_probability

safe_adjacency = threshold_by_inclusion_probability(stability.inclusion_probability, threshold=0.9)
```

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

## Goodness-of-fit (AIC/BIC/EBIC)

Everything above answers "how reliable is this estimate." A different
question -- does this structure fit the data well *at all* --
`fit_gaussian_graphical_model` answers, given any adjacency matrix
(from any of the four fit functions, or your own) plus the data it was
estimated from:

```python
from gopcnet import fit_gaussian_graphical_model

fit = fit_gaussian_graphical_model(data, result.adjacency)
fit.log_likelihood
fit.aic, fit.bic, fit.ebic  # ebic_gamma defaults to 0.5, matching fit_ebicglasso's own default
fit.precision, fit.covariance  # the fitted, exactly-constrained-to-adjacency MLE
```

It fits the exact maximum-likelihood Gaussian graphical model
constrained to `adjacency`'s zero pattern -- covariance selection
(Speed & Kiiveri, 1986; Whittaker, 1990), an unpenalized relative of
the graphical lasso's own coordinate-descent algorithm, run against a
support that's already fixed rather than searched for. Because
`fit_ebicglasso` only exposes EBIC internally (to pick its own best
lambda, never as a general tool), this is the only way to get a fit
statistic for `fit_gopc`/`fit_gopc_fixed_order`/`fit_pc_skeleton` at
all -- and it gives every method's structure a common, comparable
number on the same data.

`aic`/`bic` count `n_variables + n_edges` as free parameters (the
generic, textbook BIC definition); `ebic` counts `n_edges` alone,
matching `fit_ebicglasso`'s own formula exactly (Foygel & Drton, 2010)
-- not an inconsistency between the three; see `docs/decision_log.md`'s
D-058 for why each statistic's own literature definition specifies a
different count. `converged`/`n_iterations` report whether the fitting
algorithm actually converged -- worth checking on a large or poorly
conditioned network.

`fit_indices` builds on the same three-model machinery (`adjacency`
itself, the saturated/every-edge model, the null/no-edges model) to
add the SEM tradition's own fit indices:

```python
from gopcnet import fit_indices

indices = fit_indices(data, result.adjacency)
indices.chi_square, indices.df, indices.p_value
indices.rmsea, indices.cfi, indices.tli, indices.srmr
```

These come with conventional interpretive cutoffs in the SEM
literature (RMSEA < .05, CFI/TLI > .95, SRMR < .08, roughly) --
**not validated for a sparse structure-learning method like GOPC or
PC**, so `fit_indices` reports only the raw numbers, never a pass/fail
judgment against them. See `docs/decision_log.md`'s D-059 for the
exact formulas (RMSEA's `n - 1` denominator, CFI/TLI's null-model
baseline, SRMR's standardized-residual convention) and the degenerate
cases (a saturated `adjacency` has `df = 0`, `rmsea = 0.0`, and an
undefined -- `nan` -- `tli`).

Both `fit_gaussian_graphical_model` and `fit_indices` are optimistic
when `adjacency` was *discovered* from the same `data` being evaluated
-- the usual pattern above. Unlike a CFA/SEM measurement model
(normally specified from theory before the data at hand is examined),
`fit_gopc`/`fit_gopc_fixed_order`/`fit_pc_skeleton`/`fit_ebicglasso`
all search this exact sample for its own structure, so part of how
well that structure then appears to fit is the search exploiting this
sample's own noise, not just recovering genuine population structure.
`train_test_fit_indices` gives the honest version: split the data,
fit the structure on the training rows only, and evaluate `fit_indices`
against both splits.

```python
from functools import partial
from gopcnet import fit_gopc, train_test_fit_indices
import numpy as np

fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
result = train_test_fit_indices(data, fit, rng=np.random.default_rng(0))

result.adjacency          # the structure, fit on the training rows only
result.in_sample.rmsea    # optimistic -- evaluated on the same rows it was fit on
result.out_of_sample.rmsea  # honest -- evaluated on rows the structure never saw
```

A large gap between `in_sample` and `out_of_sample` is itself
diagnostic: it means a meaningful part of the in-sample fit was the
structure search fitting this particular sample rather than
population-level signal. `test_proportion` (default `0.5`) controls
the split; this runs a single train/test split, not k-fold
cross-validation -- call it repeatedly with different `rng` seeds and
average if you want a lower-variance estimate. See
`docs/decision_log.md`'s D-060.

## What's in the package

`pip install`ing this package gives you `gopcnet.pipeline` (the two
`fit_gopc*` functions), `gopcnet.comparators` (`fit_ebicglasso`,
`fit_pc_skeleton`), `gopcnet.stability` (`bootstrap_edge_stability`,
`case_drop_bootstrap`, `cs_coefficient`, `bootstrap_replicates`,
`difference_test`, `threshold_by_inclusion_probability`),
`gopcnet.metrics` (`compute_centrality`, `fit_gaussian_graphical_model`,
`fit_indices`, `train_test_fit_indices`), and the `gopcnet.screening`,
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
