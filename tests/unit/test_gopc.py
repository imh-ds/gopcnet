import numpy as np

from gopcnet.pipeline import fit_gopc, fit_gopc_fixed_order
from gopcnet.pipeline.compose import compose_screen_then_prune
from gopcnet.pipeline.growing_subset_dpi import growing_subset_dpi
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def test_fit_gopc_matches_manual_screen_then_growing_subset() -> None:
    """fit_gopc is exactly screening + growing_subset_dpi, nothing more
    -- verified by reproducing it manually and comparing adjacency."""
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=500)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    data = np.column_stack([x1, x2, x3])

    adjacency = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected = growing_subset_dpi(data, screened, 0.05, max_conditioning_size=4).adjacency

    assert np.array_equal(adjacency, expected)


def test_fit_gopc_respects_max_conditioning_size() -> None:
    rng = np.random.default_rng(1)
    data = rng.normal(size=(300, 4))

    adjacency = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05, max_conditioning_size=2)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected = growing_subset_dpi(data, screened, 0.05, max_conditioning_size=2).adjacency

    assert np.array_equal(adjacency, expected)


def test_fit_gopc_fixed_order_matches_manual_screen_then_compose() -> None:
    """fit_gopc_fixed_order is exactly screening + compose_screen_then_prune,
    nothing more -- verified by reproducing it manually and comparing
    adjacency. compose_screen_then_prune itself is not touched by this
    wrapper (see gopc.py's own module docstring)."""
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=500)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    data = np.column_stack([x1, x2, x3])

    adjacency = fit_gopc_fixed_order(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected, _shapes = compose_screen_then_prune(data, screened, 0.05)

    assert np.array_equal(adjacency, expected)


def test_fit_gopc_and_fit_gopc_fixed_order_share_a_call_signature() -> None:
    """Both public entry points take the same (data, screening_alpha,
    dpi_alpha) shape and return an adjacency matrix directly, so
    switching between them is a one-line change -- the ergonomic point
    of adding fit_gopc_fixed_order as a wrapper at all."""
    rng = np.random.default_rng(2)
    data = rng.normal(size=(200, 3))

    for fit in (fit_gopc, fit_gopc_fixed_order):
        adjacency = fit(data, screening_alpha=0.05, dpi_alpha=0.05)
        assert adjacency.shape == (3, 3)
        assert adjacency.dtype == bool
        assert np.array_equal(adjacency, adjacency.T)
