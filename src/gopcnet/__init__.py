"""gopcnet: Growing-Order Partial Correlation (GOPC) network estimation.

Screens pairwise associations by Fisher-z correlation, then prunes
indirect edges with a partial-correlation conditional-independence
test motivated by the data-processing-inequality logic behind
ARACNE-style pruning. Two variants are provided (`fit_gopc`, the
recommended default, and `fit_gopc_fixed_order`); see
`gopcnet.pipeline` and this project's own paper (`manuscript/`, not
distributed with the package) for the full methodological framing and
its relationship to LOPC (Zuo, Yu, Tadesse, & Ressom, 2014) and the PC
algorithm.

    >>> from gopcnet import fit_gopc
    >>> adjacency = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.01)

Two comparator methods used throughout this project's own benchmarks
(`docs/decision_log.md`) are also exposed directly, for users who want
to benchmark GOPC against them on their own data: `fit_ebicglasso`
(graphical lasso, EBIC-selected penalty) and `fit_pc_skeleton` (the PC
algorithm's skeleton phase only, no orientation). Unlike the two
`fit_gopc*` functions, both return a small result object (with an
`.adjacency` attribute) rather than a bare array -- see each
function's own docstring.

This package was previously named `mintnet`; see README.md's "A note
on the package name" section if you find `mintnet.*` references in
this repository's own historical charters or decision log.

Only the modules re-exported here, plus `gopcnet.pipeline`,
`gopcnet.comparators`, `gopcnet.screening`, `gopcnet.dpi`, and
`gopcnet.mi`, are distributed with `pip install`; `gopcnet.experiments`,
`gopcnet.simulation`, and `gopcnet.bootstrap` are this repository's own
internal validation scaffolding and are excluded from the built
package (see `pyproject.toml`) -- they remain available when working
from a checkout of this repository itself.
"""

from gopcnet.comparators import EBICglassoResult, PCSkeletonResult, fit_ebicglasso, fit_pc_skeleton
from gopcnet.pipeline import fit_gopc, fit_gopc_fixed_order

__version__ = "0.1.0"
__all__ = [
    "fit_gopc",
    "fit_gopc_fixed_order",
    "fit_ebicglasso",
    "EBICglassoResult",
    "fit_pc_skeleton",
    "PCSkeletonResult",
    "__version__",
]
