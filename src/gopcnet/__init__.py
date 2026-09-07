"""gopcnet: Growing-Order Partial Correlation (GOPC) network estimation.

Screens pairwise associations by Fisher-z correlation, then prunes
indirect edges with a partial-correlation conditional-independence
test motivated by the data-processing-inequality logic behind
ARACNE-style pruning. Two variants are provided (`fit_gopc`, the
recommended default, and `fit_gopc_fixed_order`); see
`gopcnet.pipeline` and this project's own paper (`manuscript/`, not
distributed with the package) for the full methodological framing and
its relationship to LOPC (Zuo, Yu, Tadesse, & Ressom, 2014) and the PC
algorithm. Both return a `GOPCResult` -- `.adjacency` (boolean) and
`.weights` (signed partial correlations; see `docs/decision_log.md`'s
D-055 for the convention).

    >>> from gopcnet import fit_gopc
    >>> result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)
    >>> result.adjacency, result.weights

Two comparator methods used throughout this project's own benchmarks
(`docs/decision_log.md`) are also exposed directly, for users who want
to benchmark GOPC against them on their own data: `fit_ebicglasso`
(graphical lasso, EBIC-selected penalty) and `fit_pc_skeleton` (the PC
algorithm's skeleton phase only, no orientation). Unlike the two
`fit_gopc*` functions, both return a small result object (with an
`.adjacency` attribute) rather than a bare array -- see each
function's own docstring.

`bootstrap_edge_stability` runs a nonparametric bootstrap through any
one of the four fit functions above (bind its own hyperparameters with
`functools.partial` first) and reports each pair's edge-inclusion
frequency, plus edge-weight mean/std where a weight exists:

    >>> from functools import partial
    >>> from gopcnet import fit_gopc, bootstrap_edge_stability
    >>> import numpy as np
    >>> fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
    >>> stability = bootstrap_edge_stability(data, fit, bootstraps=1000, rng=np.random.default_rng(0))

`compute_centrality` takes any weight matrix of the same shape
(`GOPCResult.weights`, `EdgeStabilityResult.weight_mean`, or your own)
and reports `strength`, `expected_influence`, `closeness`, and
`betweenness` per node -- `closeness`/`betweenness` treat `1 / |weight|`
as each edge's distance, the qgraph/bootnet convention (see
`gopcnet.metrics.centrality`'s own module docstring for why sign
doesn't affect distance):

    >>> from gopcnet import compute_centrality
    >>> centrality = compute_centrality(result.weights)
    >>> centrality.strength, centrality.betweenness

`case_drop_bootstrap`/`cs_coefficient` answer a different reliability
question than `bootstrap_edge_stability`: not "how stable is this
edge," but "how much of my sample could I lose before a statistic
(usually a centrality measure) stops resembling the full-sample
estimate at all" -- the correlation-stability (CS) coefficient
(Epskamp, Borsboom, & Fried, 2018; see `docs/decision_log.md`'s D-056
for the exact convention):

    >>> from functools import partial
    >>> from gopcnet import fit_gopc, strength, case_drop_bootstrap, cs_coefficient
    >>> fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
    >>> case_drop = case_drop_bootstrap(
    ...     data, fit, lambda r: strength(r.weights), bootstraps_per_proportion=1000,
    ...     rng=np.random.default_rng(0),
    ... )
    >>> cs_coefficient(case_drop).cs_coefficient

`bootstrap_replicates`/`difference_test` answer yet another question:
is one specific edge (or one node's centrality) really different from
another, or is that within bootstrap noise? `bootstrap_replicates`
keeps every bootstrap replicate's raw statistic vector (rather than
aggregating, like `bootstrap_edge_stability` does), so `difference_test`
can build a paired percentile bootstrap CI for the difference between
any two of its entries (see `docs/decision_log.md`'s D-057):

    >>> from gopcnet import bootstrap_replicates, difference_test
    >>> replicates = bootstrap_replicates(
    ...     data, fit, lambda r: strength(r.weights), bootstraps=1000, rng=np.random.default_rng(0),
    ... )
    >>> difference_test(replicates, index_a=0, index_b=1)  # node 0's strength vs node 1's

`threshold_by_inclusion_probability` is a smaller, separate
convenience: turn `EdgeStabilityResult.inclusion_probability` into a
"safe" adjacency matrix directly (only edges above some inclusion
frequency survive), matching the idea behind `bootnet`'s own
`bootInclude()`.

Everything above answers "how reliable is this estimate." A different
question -- "does this structure fit the data well at all" --
`fit_gaussian_graphical_model` answers, given any adjacency (from any
of the four fit functions) plus the data: it fits the exact
maximum-likelihood Gaussian graphical model constrained to that
adjacency's zero pattern and reports `log_likelihood`, `aic`, `bic`,
and `ebic` (Foygel & Drton, 2010) -- a single, comparable number
across methods on the same data (see `docs/decision_log.md`'s D-058):

    >>> from gopcnet import fit_gaussian_graphical_model
    >>> fit = fit_gaussian_graphical_model(data, result.adjacency)
    >>> fit.aic, fit.bic, fit.ebic

This package was previously named `mintnet`; see README.md's "A note
on the package name" section if you find `mintnet.*` references in
this repository's own historical charters or decision log.

Only the modules re-exported here, plus `gopcnet.pipeline`,
`gopcnet.comparators`, `gopcnet.stability`, `gopcnet.metrics`,
`gopcnet.screening`, `gopcnet.dpi`, and `gopcnet.mi`, are distributed
with `pip install`; `gopcnet.experiments`, `gopcnet.simulation`, and
`gopcnet.bootstrap` (the older, `compose_screen_then_prune`-specific
bootstrap tool `docs/stage3_charter.md`'s own evidence was validated
against) are this repository's own internal validation scaffolding and
are excluded from the built package (see `pyproject.toml`) -- they
remain available when working from a checkout of this repository
itself. `gopcnet.metrics.score_motif` ships too but isn't re-exported
here -- it's a validation-only 3x3 motif scorer for this repository's
own benchmarks, not a tool for analyzing a real fitted network.
"""

from gopcnet.comparators import EBICglassoResult, PCSkeletonResult, fit_ebicglasso, fit_pc_skeleton
from gopcnet.metrics import (
    CentralityResult,
    GGMFitResult,
    betweenness_centrality,
    closeness_centrality,
    compute_centrality,
    expected_influence,
    fit_gaussian_graphical_model,
    strength,
)
from gopcnet.pipeline import GOPCResult, fit_gopc, fit_gopc_fixed_order
from gopcnet.stability import (
    BootstrapReplicates,
    CaseDropResult,
    CSCoefficientResult,
    DifferenceTestResult,
    EdgeStabilityResult,
    bootstrap_edge_stability,
    bootstrap_replicates,
    case_drop_bootstrap,
    cs_coefficient,
    difference_test,
    threshold_by_inclusion_probability,
)

__version__ = "0.1.0"
__all__ = [
    "fit_gopc",
    "fit_gopc_fixed_order",
    "GOPCResult",
    "fit_ebicglasso",
    "EBICglassoResult",
    "fit_pc_skeleton",
    "PCSkeletonResult",
    "bootstrap_edge_stability",
    "EdgeStabilityResult",
    "case_drop_bootstrap",
    "CaseDropResult",
    "cs_coefficient",
    "CSCoefficientResult",
    "bootstrap_replicates",
    "BootstrapReplicates",
    "difference_test",
    "DifferenceTestResult",
    "threshold_by_inclusion_probability",
    "compute_centrality",
    "CentralityResult",
    "strength",
    "expected_influence",
    "closeness_centrality",
    "betweenness_centrality",
    "fit_gaussian_graphical_model",
    "GGMFitResult",
    "__version__",
]
