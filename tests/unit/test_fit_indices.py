import math

import numpy as np
import pytest

from gopcnet import fit_gopc
from gopcnet.metrics.fit import FitIndicesResult, fit_gaussian_graphical_model, fit_indices


def _chain_data(seed: int, n: int = 500) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_saturated_adjacency_has_zero_df_and_zero_rmsea() -> None:
    data = _chain_data(0)
    p = data.shape[1]
    adjacency = np.ones((p, p), dtype=bool)
    np.fill_diagonal(adjacency, False)

    result = fit_indices(data, adjacency)

    assert result.df == 0
    assert result.chi_square == pytest.approx(0.0, abs=1e-6)
    assert result.rmsea == 0.0
    assert math.isnan(result.p_value)
    assert math.isnan(result.tli)
    assert result.cfi == pytest.approx(1.0, abs=1e-6)


def test_null_adjacency_gives_cfi_zero_by_construction() -> None:
    """When adjacency itself IS the null (independence) model, target
    and null coincide exactly -- the textbook degenerate case where
    CFI is defined as 0.0, not merely small."""
    data = _chain_data(0)
    p = data.shape[1]
    adjacency = np.zeros((p, p), dtype=bool)

    result = fit_indices(data, adjacency)

    assert result.chi_square == pytest.approx(0.0, abs=1e-6) or result.chi_square == pytest.approx(
        2.0 * (result.saturated.log_likelihood - result.null.log_likelihood)
    )
    assert result.cfi == pytest.approx(0.0, abs=1e-6)


def test_df_equals_non_edges() -> None:
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_indices(data, fitted.adjacency)

    p = fitted.adjacency.shape[0]
    total_pairs = p * (p - 1) // 2
    assert result.df == total_pairs - result.target.n_edges


def test_chi_square_matches_manual_formula() -> None:
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_indices(data, fitted.adjacency)

    expected_chi_square = max(0.0, 2.0 * (result.saturated.log_likelihood - result.target.log_likelihood))
    assert result.chi_square == pytest.approx(expected_chi_square)


def test_rmsea_matches_manual_formula_when_df_positive() -> None:
    data = _chain_data(0, n=600)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_indices(data, fitted.adjacency)

    assert result.df > 0  # sanity: this structure isn't saturated
    n = data.shape[0]
    expected_rmsea = math.sqrt(max(result.chi_square - result.df, 0.0) / (result.df * (n - 1)))
    assert result.rmsea == pytest.approx(expected_rmsea)


def test_srmr_is_zero_for_the_saturated_model() -> None:
    """The saturated model's fitted covariance equals the sample
    covariance exactly (no constraints at all) -- SRMR must be ~0."""
    data = _chain_data(0)
    p = data.shape[1]
    adjacency = np.ones((p, p), dtype=bool)
    np.fill_diagonal(adjacency, False)

    result = fit_indices(data, adjacency)
    assert result.srmr == pytest.approx(0.0, abs=1e-6)


def test_indices_are_in_mathematically_valid_ranges_on_a_real_structure() -> None:
    data = _chain_data(2, n=700)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_indices(data, fitted.adjacency)

    assert isinstance(result, FitIndicesResult)
    assert result.chi_square >= 0.0
    assert result.rmsea >= 0.0
    assert result.srmr >= 0.0
    assert result.cfi <= 1.0 + 1e-8
    if result.df > 0:
        assert 0.0 <= result.p_value <= 1.0


def test_fit_indices_reuses_fit_gaussian_graphical_model_consistently() -> None:
    """target/saturated/null should each be exactly what a direct
    fit_gaussian_graphical_model call on the same adjacency produces."""
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_indices(data, fitted.adjacency)

    direct_target = fit_gaussian_graphical_model(data, fitted.adjacency)
    assert result.target.log_likelihood == pytest.approx(direct_target.log_likelihood)
    assert result.target.n_edges == direct_target.n_edges
