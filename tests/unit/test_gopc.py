import numpy as np

from gopcnet.pipeline import fit_gopc, fit_gopc_fixed_order
from gopcnet.pipeline.compose import compose_screen_then_prune
from gopcnet.pipeline.growing_subset_dpi import growing_subset_dpi
from gopcnet.pipeline.weights import compute_fixed_order_weights, compute_growing_order_weights
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def test_fit_gopc_matches_manual_screen_then_growing_subset() -> None:
    """fit_gopc is exactly screening + growing_subset_dpi, nothing more
    -- verified by reproducing it manually and comparing adjacency."""
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=500)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    data = np.column_stack([x1, x2, x3])

    result = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected = growing_subset_dpi(data, screened, 0.05, max_conditioning_size=4).adjacency

    assert np.array_equal(result.adjacency, expected)


def test_fit_gopc_respects_max_conditioning_size() -> None:
    rng = np.random.default_rng(1)
    data = rng.normal(size=(300, 4))

    result = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05, max_conditioning_size=2)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected = growing_subset_dpi(data, screened, 0.05, max_conditioning_size=2).adjacency

    assert np.array_equal(result.adjacency, expected)


def test_fit_gopc_matches_manual_growing_order_weights() -> None:
    """fit_gopc's own .weights matches compute_growing_order_weights fed
    the exact growing_subset_dpi call it wraps -- verified by
    reproducing both manually and comparing."""
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=500)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    data = np.column_stack([x1, x2, x3])

    result = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    dpi_result = growing_subset_dpi(data, screened, 0.05, max_conditioning_size=4)
    expected_weights = compute_growing_order_weights(
        data, dpi_result.adjacency, screened, dpi_result.conditioning_size_used, max_conditioning_size=4
    )

    assert np.allclose(result.weights, expected_weights)


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

    result = fit_gopc_fixed_order(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    expected, _shapes = compose_screen_then_prune(data, screened, 0.05)

    assert np.array_equal(result.adjacency, expected)


def test_fit_gopc_fixed_order_matches_manual_fixed_order_weights() -> None:
    rng = np.random.default_rng(0)
    x1 = rng.normal(size=500)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=500)
    data = np.column_stack([x1, x2, x3])

    result = fit_gopc_fixed_order(data, screening_alpha=0.05, dpi_alpha=0.05)

    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, 0.05)
    final, shapes = compose_screen_then_prune(data, screened, 0.05)
    expected_weights = compute_fixed_order_weights(data, final, shapes)

    assert np.allclose(result.weights, expected_weights)


def test_fit_gopc_and_fit_gopc_fixed_order_share_a_call_signature() -> None:
    """Both public entry points take the same (data, screening_alpha,
    dpi_alpha) shape and return a GOPCResult, so switching between them
    is a one-line change -- the ergonomic point of adding
    fit_gopc_fixed_order as a wrapper at all."""
    rng = np.random.default_rng(2)
    data = rng.normal(size=(200, 3))

    for fit in (fit_gopc, fit_gopc_fixed_order):
        result = fit(data, screening_alpha=0.05, dpi_alpha=0.05)
        assert result.adjacency.shape == (3, 3)
        assert result.adjacency.dtype == bool
        assert np.array_equal(result.adjacency, result.adjacency.T)
        assert result.weights.shape == (3, 3)
        assert np.allclose(result.weights, result.weights.T)
        assert np.all(np.diag(result.weights) == 0.0)
        assert np.all(result.weights[~result.adjacency] == 0.0)
