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
