import numpy as np
import pytest

from gopcnet import fit_ebicglasso, fit_gopc
from gopcnet.metrics.fit import GGMFitResult, fit_gaussian_graphical_model


def _chain_data(seed: int, n: int = 500) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = 0.6 * x1 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    x3 = 0.6 * x2 + np.sqrt(1 - 0.6**2) * rng.normal(size=n)
    return np.column_stack([x1, x2, x3])


def test_complete_graph_reduces_to_the_unconstrained_mle() -> None:
    """With every edge present, covariance selection imposes no
    constraint at all -- the fitted precision must equal the exact
    inverse of the sample covariance."""
    data = _chain_data(0)
    p = data.shape[1]
    adjacency = np.ones((p, p), dtype=bool)
    np.fill_diagonal(adjacency, False)

    result = fit_gaussian_graphical_model(data, adjacency)

    sample_covariance = np.cov(data, rowvar=False, ddof=0)
    expected_precision = np.linalg.inv(sample_covariance)
    assert np.allclose(result.precision, expected_precision, atol=1e-6)
    assert result.converged


def test_empty_graph_reduces_to_the_independence_model() -> None:
    """With no edges at all, the constrained MLE is exactly the
    diagonal (independence) model: 1/variance on the diagonal, zero
    off-diagonal."""
    data = _chain_data(0)
    p = data.shape[1]
    adjacency = np.zeros((p, p), dtype=bool)

    result = fit_gaussian_graphical_model(data, adjacency)

    sample_covariance = np.cov(data, rowvar=False, ddof=0)
    expected_precision = np.diag(1.0 / np.diag(sample_covariance))
    assert np.allclose(result.precision, expected_precision, atol=1e-6)
    assert result.n_edges == 0
    assert result.n_parameters == p


def test_covariance_selection_defining_property_on_a_real_chain_structure() -> None:
    """The fitted covariance must match the sample covariance exactly
    on the diagonal and at every edge -- this is what "covariance
    selection MLE" means, not an approximate property."""
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    adjacency = fitted.adjacency

    result = fit_gaussian_graphical_model(data, adjacency)
    sample_covariance = np.cov(data, rowvar=False, ddof=0)

    p = adjacency.shape[0]
    assert np.allclose(np.diag(result.covariance), np.diag(sample_covariance), atol=1e-6)
    for i in range(p):
        for j in range(p):
            if i != j and adjacency[i, j]:
                assert result.covariance[i, j] == pytest.approx(sample_covariance[i, j], abs=1e-6)

    # And the precision matrix must be exactly zero at every non-edge.
    for i in range(p):
        for j in range(p):
            if i != j and not adjacency[i, j]:
                assert result.precision[i, j] == pytest.approx(0.0, abs=1e-8)


def test_aic_bic_ebic_match_manual_formula_reconstruction() -> None:
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_gaussian_graphical_model(data, fitted.adjacency, ebic_gamma=0.5)

    n, p = data.shape
    expected_aic = -2.0 * result.log_likelihood + 2.0 * result.n_parameters
    expected_bic = -2.0 * result.log_likelihood + result.n_parameters * np.log(n)
    expected_ebic = (
        -2.0 * result.log_likelihood
        + result.n_edges * np.log(n)
        + 4.0 * 0.5 * result.n_edges * np.log(p)
    )

    assert result.aic == pytest.approx(expected_aic)
    assert result.bic == pytest.approx(expected_bic)
    assert result.ebic == pytest.approx(expected_ebic)


def test_bic_and_ebic_use_different_parameter_counts_by_design() -> None:
    """AIC/BIC count n_variables + n_edges; EBIC counts n_edges alone
    -- per each statistic's own literature definition, not an
    inconsistency (see docs/decision_log.md's D-058)."""
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_gaussian_graphical_model(data, fitted.adjacency)

    p = fitted.adjacency.shape[0]
    assert result.n_parameters == p + result.n_edges
    if result.n_edges > 0:
        assert result.n_parameters != result.n_edges


def test_exact_mle_refit_never_scores_lower_than_glassos_own_penalized_fit() -> None:
    """A real mathematical property, not a tuned expectation: the
    unconstrained MLE for a fixed support maximizes likelihood over
    every matrix sharing that support, so refitting fit_ebicglasso's
    own selected support exactly can never score a lower log-likelihood
    than glasso's own (necessarily shrunk) fit at that same support."""
    data = _chain_data(1, n=600)
    glasso_result = fit_ebicglasso(data)

    def _log_likelihood(precision: np.ndarray, sample_covariance: np.ndarray, n: int) -> float:
        p = precision.shape[0]
        sign, log_det = np.linalg.slogdet(precision)
        assert sign > 0
        return 0.5 * n * (log_det - p * np.log(2 * np.pi) - np.trace(sample_covariance @ precision))

    n = data.shape[0]
    sample_covariance = np.cov(data, rowvar=False, ddof=0)
    glasso_log_likelihood = _log_likelihood(glasso_result.precision, sample_covariance, n)

    refit = fit_gaussian_graphical_model(data, glasso_result.adjacency)

    assert refit.log_likelihood >= glasso_log_likelihood - 1e-8


def test_rejects_mismatched_adjacency_shape() -> None:
    data = _chain_data(0)
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, np.zeros((2, 2), dtype=bool))


def test_rejects_asymmetric_adjacency() -> None:
    data = _chain_data(0)
    adjacency = np.array([[False, True, False], [False, False, False], [False, False, False]])
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, adjacency)


def test_rejects_nonzero_diagonal() -> None:
    data = _chain_data(0)
    adjacency = np.eye(3, dtype=bool)
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, adjacency)


def test_rejects_more_columns_than_rows() -> None:
    data = np.random.default_rng(0).normal(size=(3, 5))
    adjacency = np.zeros((5, 5), dtype=bool)
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, adjacency)


def test_rejects_invalid_ebic_gamma() -> None:
    data = _chain_data(0)
    adjacency = np.zeros((3, 3), dtype=bool)
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, adjacency, ebic_gamma=0.0)
    with pytest.raises(ValueError):
        fit_gaussian_graphical_model(data, adjacency, ebic_gamma=1.5)


def test_returns_ggm_fit_result_with_sane_shapes() -> None:
    data = _chain_data(0)
    fitted = fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
    result = fit_gaussian_graphical_model(data, fitted.adjacency)

    assert isinstance(result, GGMFitResult)
    assert result.precision.shape == (3, 3)
    assert result.covariance.shape == (3, 3)
    # np.linalg.inv of an exactly-symmetric matrix isn't guaranteed to be
    # bit-for-bit symmetric -- only symmetric up to floating-point noise.
    assert np.allclose(result.precision, result.precision.T, atol=1e-8)
    assert isinstance(result.converged, bool)
    assert result.n_iterations >= 1
