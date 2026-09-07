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

This package was previously named `mintnet`; see README.md's "A note
on the package name" section if you find `mintnet.*` references in
this repository's own historical charters or decision log.
"""

from gopcnet.pipeline import fit_gopc, fit_gopc_fixed_order

__version__ = "0.1.0"
__all__ = ["fit_gopc", "fit_gopc_fixed_order", "__version__"]
