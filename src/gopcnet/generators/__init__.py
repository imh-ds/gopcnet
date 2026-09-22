"""Data generators shipped with the package (unlike `gopcnet.simulation`,
which is internal validation scaffolding excluded from `pip install`).

Everything here samples through `gopcnet.generators.sampling`'s
Cholesky-based sampler -- see that module's docstring and
`docs/decision_log.md`'s D-065 for why new generators never use
`numpy.random.Generator.multivariate_normal`.
"""

from .psych_networks import STRUCTURES, PsychTruth, make_truth, sample_data
from .sampling import cholesky_factor, covariance_from_precision, sample_gaussian

__all__ = [
    "STRUCTURES",
    "PsychTruth",
    "make_truth",
    "sample_data",
    "cholesky_factor",
    "covariance_from_precision",
    "sample_gaussian",
]
