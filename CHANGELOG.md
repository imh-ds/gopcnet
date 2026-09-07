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

## 0.1.0

Initial state at the time of the `mintnet` -> `gopcnet` rename:
`fit_gopc` (growing-order GOPC, the recommended default per
`docs/decision_log.md`'s D-053) and `compose_screen_then_prune`
(fixed-order GOPC's own frozen mechanism) available via
`gopcnet.pipeline`.
