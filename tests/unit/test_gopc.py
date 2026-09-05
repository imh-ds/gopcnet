import numpy as np

from mintnet.pipeline import fit_gopc
from mintnet.pipeline.growing_subset_dpi import growing_subset_dpi
from mintnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


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
