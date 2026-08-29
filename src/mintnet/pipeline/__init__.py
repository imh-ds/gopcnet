"""Composition of screening and DPI pruning mechanisms."""

from .compose import (
    VALIDATED_CLIQUE_SIZES,
    compose_screen_then_prune,
    connected_components,
    describe_component,
)

__all__ = [
    "compose_screen_then_prune",
    "connected_components",
    "describe_component",
    "VALIDATED_CLIQUE_SIZES",
]
