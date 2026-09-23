import numpy as np
import pytest

from gopcnet import fit_gopc
from gopcnet.comparators.nonregularized import fit_nonregularized_ggm
from gopcnet.pipeline.weights import refit_weights, refit_weights_from_correlation


def _chain(n: int, p: int, rho: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    columns = [rng.normal(size=n)]
    for _ in range(p - 1):
        columns.append(rho * columns[-1] + np.sqrt(1 - rho**2) * rng.normal(size=n))
    return np.column_stack(columns)


def test_saturated_support_gives_full_order_partial_correlations() -> None:
    data = np.random.default_rng(0).normal(size=(400, 6)) @ np.triu(np.ones((6, 6))) / 3
    saturated = ~np.eye(6, dtype=bool)

    refit = refit_weights(data, saturated)

    expected = fit_nonregularized_ggm(data, correction="none").partial_correlations
    assert np.allclose(refit, expected, atol=1e-6)


def test_empty_support_gives_all_zeros() -> None:
    assert (refit_weights(_chain(300, 4, 0.5, seed=1), np.zeros((4, 4), dtype=bool)) == 0.0).all()


def test_support_is_preserved_and_matrix_symmetric() -> None:
    data = _chain(800, 5, 0.5, seed=2)
    chain_support = np.zeros((5, 5), dtype=bool)
    for k in range(4):
        chain_support[k, k + 1] = chain_support[k + 1, k] = True

    refit = refit_weights(data, chain_support)

    assert np.array_equal(refit != 0.0, chain_support)
    assert np.allclose(refit, refit.T)


def test_correlation_and_covariance_input_agree() -> None:
    data = _chain(500, 4, 0.5, seed=3) * np.array([1.0, 3.0, 0.5, 2.0])
    support = np.ones((4, 4), dtype=bool) & ~np.eye(4, dtype=bool)
    support[0, 3] = support[3, 0] = False

    from_corr = refit_weights_from_correlation(np.corrcoef(data, rowvar=False), support)
    from_cov = refit_weights_from_correlation(np.cov(data, rowvar=False), support)

    assert np.allclose(from_corr, from_cov, atol=1e-6)


@pytest.mark.parametrize("engine", ["component", "adjacency"])
def test_fit_gopc_refit_changes_weights_not_structure(engine: str) -> None:
    data = _chain(1000, 5, 0.5, seed=4)

    default = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.05, engine=engine)
    refit = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.05, engine=engine, weight_method="refit")

    assert np.array_equal(default.adjacency, refit.adjacency)
    assert np.allclose(refit.weights, refit_weights(data, default.adjacency))


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError):
        refit_weights(np.zeros((3, 5)), np.zeros((5, 5), dtype=bool))  # N <= p
    with pytest.raises(ValueError):
        refit_weights_from_correlation(np.eye(3), np.eye(3, dtype=bool))  # True diagonal
    with pytest.raises(ValueError):
        fit_gopc(_chain(200, 3, 0.5, seed=5), screening_alpha=0.01, dpi_alpha=0.05, weight_method="glasso")
