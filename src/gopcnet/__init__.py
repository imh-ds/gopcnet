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

This package was previously named `mintnet`; see README.md's "A note
on the package name" section if you find `mintnet.*` references in
this repository's own historical charters or decision log.

Only the modules re-exported here, plus `gopcnet.pipeline`,
`gopcnet.comparators`, `gopcnet.stability`, `gopcnet.screening`,
`gopcnet.dpi`, and `gopcnet.mi`, are distributed with `pip install`;
`gopcnet.experiments`, `gopcnet.simulation`, and `gopcnet.bootstrap`
(the older, `compose_screen_then_prune`-specific bootstrap tool
`docs/stage3_charter.md`'s own evidence was validated against) are
this repository's own internal validation scaffolding and are excluded
from the built package (see `pyproject.toml`) -- they remain available
when working from a checkout of this repository itself.
"""

from gopcnet.comparators import EBICglassoResult, PCSkeletonResult, fit_ebicglasso, fit_pc_skeleton
from gopcnet.pipeline import GOPCResult, fit_gopc, fit_gopc_fixed_order
from gopcnet.stability import EdgeStabilityResult, bootstrap_edge_stability

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
    "__version__",
]
