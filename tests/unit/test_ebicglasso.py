import numpy as np

from mintnet.comparators.ebicglasso import fit_ebicglasso


def test_fit_ebicglasso_recovers_sparse_structure_at_large_n() -> None:
    precision = np.array(
        [
            [1.0, -0.4, 0.0],
            [-0.4, 1.0, -0.4],
            [0.0, -0.4, 1.0],
        ]
    )
    covariance = np.linalg.inv(precision)
    rng = np.random.default_rng(0)
    data = rng.multivariate_normal(np.zeros(3), covariance, size=5000)

    result = fit_ebicglasso(data)

    assert result.adjacency[0, 1] and result.adjacency[1, 0]
    assert result.adjacency[1, 2] and result.adjacency[2, 1]
    assert not result.adjacency[0, 2] and not result.adjacency[2, 0]
    assert not result.adjacency.diagonal().any()
    assert result.n_edges == 2


def test_fit_ebicglasso_null_data_yields_sparse_or_empty_graph() -> None:
    rng = np.random.default_rng(1)
    data = rng.normal(size=(2000, 5))

    result = fit_ebicglasso(data)

    assert result.n_edges <= 1  # EBIC's own log(p) penalty should reject nearly all noise edges


def test_fit_ebicglasso_lambda_grid_is_descending_from_sparse_to_dense() -> None:
    rng = np.random.default_rng(2)
    data = rng.normal(size=(500, 4))

    result = fit_ebicglasso(data, n_lambda=10)

    assert result.lambda_grid[0] > result.lambda_grid[-1]
    assert len(result.lambda_grid) == 10
    assert len(result.ebic_by_lambda) == 10
