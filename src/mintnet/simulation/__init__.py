"""Known-truth simulation data generators."""

from .motifs import (
    sample_chain,
    sample_measured_fork,
    sample_precision_triangle,
    triangle_precisions,
)

__all__ = [
    "sample_chain",
    "sample_measured_fork",
    "sample_precision_triangle",
    "triangle_precisions",
]
