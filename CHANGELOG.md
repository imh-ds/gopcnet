# Changelog

All notable changes to this package are recorded here. This tracks the
package's own public API and installability; it is not a substitute
for `docs/decision_log.md`, which tracks the scientific/methodological
validation history in full.

## [Unreleased]

### Changed
- Renamed the importable package from `mintnet` to `gopcnet`
  (`pip install git+https://github.com/imh-ds/gopcnet.git`, then
  `from gopcnet import fit_gopc`). `mintnet.*` import paths no longer
  work. See README.md's "A note on the package name" for why.
- `fit_gopc` and `fit_gopc_fixed_order` are now importable directly
  from the top-level package (`from gopcnet import fit_gopc`), not
  only from `gopcnet.pipeline`.
- **Breaking:** `fit_gopc` and `fit_gopc_fixed_order` now return a
  `GOPCResult(adjacency, weights)` dataclass instead of a bare boolean
  array. `result.adjacency` is the same array either function returned
  before; `result.weights` is new (see Added, below). Update
  `adjacency = fit_gopc(...)` call sites to
  `result = fit_gopc(...); result.adjacency`.

### Added
- `fit_gopc_fixed_order`: a convenience wrapper around
  `compose_screen_then_prune` with the same call signature as
  `fit_gopc`, so both of the paper's GOPC variants are equally easy to
  use. `compose_screen_then_prune` itself is unchanged and still
  directly exported.
- Full parameter/return-value docstrings, with a verified, runnable
  example, on both `fit_gopc` and `fit_gopc_fixed_order`.
- Package-level docstring and `__version__`.
- Installation instructions in README.md (GitHub install; not yet
  published to PyPI).
- `fit_ebicglasso` and `fit_pc_skeleton` (with their `EBICglassoResult`
  and `PCSkeletonResult` result types) are now importable from the
  top-level package, alongside `gopcnet.comparators` where they already
  lived, so users can benchmark GOPC against them without reaching
  into a submodule.
- Weighted edges: both `fit_gopc*` functions' `GOPCResult.weights` is a
  signed, symmetric partial-correlation matrix (zero where `.adjacency`
  is False), computed by the new `gopcnet.pipeline.weights` module
  without changing either underlying pruning mechanism's decision
  logic. See README.md's "Edge weights" section and
  `docs/decision_log.md`'s D-055 for the convention (it differs by
  variant, and for whether an edge was ever conditioning-tested).
- `bootstrap_edge_stability` (top-level, alongside its
  `EdgeStabilityResult` return type): a generic nonparametric bootstrap
  usable with any of the four fit functions -- bind a method's own
  hyperparameters with `functools.partial` and pass it in. Reports each
  pair's edge-inclusion frequency across resamples, plus
  weight mean/std for the two `fit_gopc*` functions (`None` for the
  comparators, which don't define an edge weight). Lives in the new
  `gopcnet.stability` module, distinct from the older,
  `compose_screen_then_prune`-specific `gopcnet.bootstrap` tool (which
  is unchanged, stays internal, and now delegates its own
  `bootstrap_resample` to `gopcnet.stability`'s copy rather than
  duplicating it).
- `compute_centrality` (top-level, alongside its `CentralityResult`
  return type, and the four individual measures it bundles --
  `strength`, `expected_influence`, `closeness_centrality`,
  `betweenness_centrality`): standard node centrality for any weighted
  network of the shape `fit_gopc`/`fit_gopc_fixed_order`/
  `bootstrap_edge_stability` already produce. `closeness`/`betweenness`
  use `1 / |weight|` as each edge's distance (qgraph/bootnet
  convention -- sign doesn't affect distance, only
  `expected_influence`). Betweenness uses the full Brandes (2001)
  algorithm, splitting tied shortest paths proportionally rather than
  picking one arbitrarily. Lives in the new
  `gopcnet.metrics.centrality` module.
- `case_drop_bootstrap`/`cs_coefficient` (top-level, alongside their
  `CaseDropResult`/`CSCoefficientResult` return types): the
  correlation-stability (CS) coefficient (Epskamp, Borsboom, & Fried,
  2018) -- `bootnet`'s own signature reliability diagnostic, and
  distinct from `bootstrap_edge_stability`'s edge-inclusion stability.
  `case_drop_bootstrap` subsamples without replacement at shrinking
  sample sizes, running any of the four fit functions plus a
  caller-supplied statistic function; `cs_coefficient` reduces that to
  a single coefficient (Spearman correlation, the literature's own
  0.7/0.95 thresholds by default, a monotonic pass-rate rule). See
  README.md's "Correlation-stability (CS) coefficient" section and
  `docs/decision_log.md`'s D-056 for the exact convention.
- `bootstrap_replicates`/`difference_test` (top-level, alongside their
  `BootstrapReplicates`/`DifferenceTestResult` return types): test
  whether one edge or node's statistic really differs from another's,
  or is within bootstrap noise -- `bootnet`'s `differenceTest()`.
  `bootstrap_replicates` runs the same nonparametric bootstrap
  `bootstrap_edge_stability` does but keeps every replicate's raw
  statistic vector; `difference_test` builds a paired percentile
  bootstrap CI on the difference between two of its entries (per
  replicate, not from independently-combined means/stds, so
  correlated variability between the two is preserved). See
  `docs/decision_log.md`'s D-057.
- `threshold_by_inclusion_probability` (top-level): turn an
  `EdgeStabilityResult.inclusion_probability` matrix directly into a
  "safe" adjacency matrix (only edges above some inclusion frequency
  survive) -- matches the idea behind `bootnet`'s `bootInclude()`.
- `fit_gaussian_graphical_model` (top-level, alongside its
  `GGMFitResult` return type): absolute goodness-of-fit for any
  adjacency matrix (from any of the four fit functions, or your own)
  -- fits the exact maximum-likelihood Gaussian graphical model
  constrained to that adjacency's zero pattern (covariance selection;
  Speed & Kiiveri, 1986) and reports `log_likelihood`, `aic`, `bic`,
  and `ebic` (Foygel & Drton, 2010). Unlike `fit_ebicglasso`'s own
  internal EBIC (used only to pick its best lambda), this is a
  general-purpose tool: the only way to get a fit statistic at all for
  `fit_gopc`/`fit_gopc_fixed_order`/`fit_pc_skeleton`, and a common
  number to compare any two methods' structures on the same data. See
  README.md's "Goodness-of-fit (AIC/BIC/EBIC)" section and
  `docs/decision_log.md`'s D-058 for why AIC/BIC and EBIC count free
  parameters differently. Lives in the new `gopcnet.metrics.fit`
  module.
- `fit_indices` (top-level, alongside its `FitIndicesResult` return
  type): the SEM tradition's own fit indices -- chi-square/df/p-value,
  RMSEA, CFI, TLI, and SRMR -- for any adjacency matrix, built from
  three `fit_gaussian_graphical_model` calls (the given adjacency, the
  saturated model, the null model) with no new fitting algorithm.
  Reports raw values only, deliberately never a pass/fail judgment
  against the SEM literature's conventional cutoffs (RMSEA < .05,
  CFI/TLI > .95, SRMR < .08), since those were never validated for a
  sparse structure-learning method like GOPC or PC. See README.md's
  "Goodness-of-fit (AIC/BIC/EBIC)" section and `docs/decision_log.md`'s
  D-059 for the exact formulas and degenerate-case handling (a
  saturated adjacency has `df = 0`, `rmsea = 0.0`, and an undefined
  `tli`). Lives in `gopcnet.metrics.fit` alongside
  `fit_gaussian_graphical_model`.
- `train_test_fit_indices` (top-level, alongside its
  `TrainTestFitResult` return type): out-of-sample goodness-of-fit,
  for when `adjacency` was *discovered* from the same data being
  evaluated (the default usage pattern for `fit_indices`) rather than
  specified in advance the way a CFA/SEM measurement model normally
  is -- evaluating fit on the same sample a structure was searched
  from is optimistic, since some of the apparent fit is the search
  exploiting that sample's own noise. Splits `data` by row, runs any
  of the four fit functions (bound with `functools.partial`, the same
  convention as `bootstrap_edge_stability`) on the training rows only,
  and reports `fit_indices` against both the training rows
  (`in_sample`) and the held-out rows (`out_of_sample`). See
  `docs/decision_log.md`'s D-060. Lives in `gopcnet.metrics.fit`
  alongside `fit_gaussian_graphical_model` and `fit_indices`.
- `compute_global_metrics` (top-level, alongside its
  `GlobalMetricsResult` return type, and the four individual measures
  it bundles -- `density`, `global_strength`,
  `global_clustering_coefficient`, `average_shortest_path_length`):
  whole-network summary statistics, as distinct from every other
  metric in the package, which describes an individual edge or node.
  `global_strength` matches bootnet's own definition (sum of `|weight|`
  over every edge) so a future network comparison test can reuse it
  directly; `global_clustering_coefficient` uses the binary adjacency,
  not a weighted variant (no consensus convention exists for folding
  signed weights into one); `average_shortest_path_length` reuses
  `compute_centrality`'s own `1 / |weight|` distance convention. See
  README.md's "Whole-network summary statistics" section and
  `docs/decision_log.md`'s D-061 for why small-worldness was
  deliberately left out of this pass. Lives in the new
  `gopcnet.metrics.global_metrics` module.

### Removed
- `gopcnet.experiments`, `gopcnet.simulation`, and `gopcnet.bootstrap`
  -- this repository's own internal benchmark-running and validation
  scaffolding -- are no longer included in the built/installed
  package (`pyproject.toml`'s `packages.find` now excludes them). They
  remain in this repository and remain tested; only what `pip install`
  ships has changed. Nothing in `gopcnet.pipeline` or
  `gopcnet.comparators` ever depended on them.

## 0.1.0

Initial state at the time of the `mintnet` -> `gopcnet` rename:
`fit_gopc` (growing-order GOPC, the recommended default per
`docs/decision_log.md`'s D-053) and `compose_screen_then_prune`
(fixed-order GOPC's own frozen mechanism) available via
`gopcnet.pipeline`.
