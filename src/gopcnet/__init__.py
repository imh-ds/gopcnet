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

`fit_indices` builds on the same three-model machinery to add the
SEM-tradition fit indices -- RMSEA, CFI, TLI, and SRMR -- comparing
`adjacency` against the saturated (every edge) and null (no edges)
models. These come with conventional interpretive cutoffs in the SEM
literature that have not been validated for a sparse structure-learning
method like GOPC or PC, so only the raw values are reported, never a
pass/fail judgment (see `docs/decision_log.md`'s D-059):

    >>> from gopcnet import fit_indices
    >>> indices = fit_indices(data, result.adjacency)
    >>> indices.rmsea, indices.cfi, indices.tli, indices.srmr

Both `fit_gaussian_graphical_model` and `fit_indices` are optimistic
when `adjacency` was *discovered* from the same data being evaluated
(the usual case) -- the structure search already picked the sparsity
pattern that best explains this sample's own noise, not just its
population structure. `train_test_fit_indices` removes that bias: it
splits `data`, runs a fit function (bound with `functools.partial`,
the same convention as `bootstrap_edge_stability`) on the training
rows only, and reports `fit_indices` for the resulting structure
against both splits, so `out_of_sample` is a fair, non-circular fit
statistic (see `docs/decision_log.md`'s D-060):

    >>> from functools import partial
    >>> from gopcnet import fit_gopc, train_test_fit_indices
    >>> fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
    >>> result = train_test_fit_indices(data, fit, rng=np.random.default_rng(0))
    >>> result.in_sample.rmsea, result.out_of_sample.rmsea

`compute_global_metrics` summarizes a network as a single set of
numbers rather than per-edge or per-node values: `density`,
`global_strength` (sum of `|weight|` over every edge -- what bootnet's
own network comparison test checks for invariance between two
networks), `global_clustering_coefficient` (transitivity, from the
binary adjacency), and `average_shortest_path_length` (mean geodesic
distance, same `1 / |weight|` convention as `compute_centrality`'s
closeness/betweenness). See `docs/decision_log.md`'s D-061:

    >>> from gopcnet import compute_global_metrics
    >>> summary = compute_global_metrics(result.adjacency, result.weights)
    >>> summary.density, summary.global_strength, summary.clustering_coefficient

`network_comparison_test` answers a different question than any of the
above: do *two independent samples'* networks differ, not just how
reliable is one network's own estimate? It's bootnet's network
comparison test (NCT; van Borkulo et al., 2017) -- pool the two
samples, repeatedly re-split the pooled sample at random into groups
of the same sizes as the real two, refit under each re-split, and see
how often a random re-split produces a global-strength or maximum-edge-weight
difference at least as large as the one actually observed:

    >>> from functools import partial
    >>> from gopcnet import fit_gopc, network_comparison_test
    >>> fit = partial(fit_gopc, screening_alpha=0.01, dpi_alpha=0.05)
    >>> result = network_comparison_test(
    ...     data_group_a, data_group_b, fit, permutations=1000, rng=np.random.default_rng(0),
    ... )
    >>> result.global_strength_p_value, result.max_edge_weight_difference_p_value

See `docs/decision_log.md`'s D-062 for the exact conventions (add-one
p-value smoothing, and why only `fit_gopc`/`fit_gopc_fixed_order` --
the two weighted fit methods -- work with this function).

`compute_bridge_centrality` restricts `compute_centrality`'s own four
measures to *cross-community* relationships (Jones, Ma, & McNally,
2021) -- how much a node connects two different communities, rather
than how central it is overall. `communities` (one label per node) is
always caller-supplied; `gopcnet` has no community-detection algorithm
of its own (see `docs/decision_log.md`'s D-063 for that scope
decision):

    >>> from gopcnet import compute_bridge_centrality
    >>> communities = np.array([0, 0, 1, 1])  # your own theory or clustering
    >>> bridges = compute_bridge_centrality(result.weights, communities)
    >>> bridges.strength, bridges.betweenness

This package was previously named `mintnet`; see README.md's "A note
on the package name" section if you find `mintnet.*` references in
this repository's own historical charters or decision log.

Only the modules re-exported here, plus `gopcnet.pipeline`,
`gopcnet.comparators`, `gopcnet.stability`, `gopcnet.metrics`,
`gopcnet.network_comparison`, `gopcnet.screening`, `gopcnet.dpi`, and
`gopcnet.mi`, are distributed with `pip install`; `gopcnet.experiments`, `gopcnet.simulation`, and
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
    BridgeCentralityResult,
    CentralityResult,
    FitIndicesResult,
    GGMFitResult,
    GlobalMetricsResult,
    TrainTestFitResult,
    average_shortest_path_length,
    betweenness_centrality,
    bridge_betweenness_centrality,
    bridge_closeness_centrality,
    bridge_expected_influence,
    bridge_strength,
    closeness_centrality,
    compute_bridge_centrality,
    compute_centrality,
    compute_global_metrics,
    density,
    expected_influence,
    fit_gaussian_graphical_model,
    fit_indices,
    global_clustering_coefficient,
    global_strength,
    strength,
    train_test_fit_indices,
)
from gopcnet.network_comparison import NetworkComparisonResult, network_comparison_test
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
    "fit_indices",
    "FitIndicesResult",
    "train_test_fit_indices",
    "TrainTestFitResult",
    "compute_global_metrics",
    "GlobalMetricsResult",
    "density",
    "global_strength",
    "global_clustering_coefficient",
    "average_shortest_path_length",
    "network_comparison_test",
    "NetworkComparisonResult",
    "compute_bridge_centrality",
    "BridgeCentralityResult",
    "bridge_strength",
    "bridge_expected_influence",
    "bridge_closeness_centrality",
    "bridge_betweenness_centrality",
    "__version__",
]
