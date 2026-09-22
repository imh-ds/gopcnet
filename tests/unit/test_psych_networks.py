import numpy as np
import pytest

from gopcnet.generators.psych_networks import (
    MIN_PRECISION_EIGENVALUE,
    STRUCTURES,
    erdos_renyi,
    make_truth,
    sample_data,
    stochastic_block,
    watts_strogatz,
)


@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("p", [10, 20, 30])
def test_truths_are_valid_ggms(structure: str, p: int) -> None:
    rng = np.random.default_rng(p)
    for _ in range(40):
        truth = make_truth(structure, p, rng)
        partial = truth.partial_correlations
        precision = np.eye(p) - partial

        assert np.linalg.eigvalsh(precision).min() >= MIN_PRECISION_EIGENVALUE - 1e-9
        assert np.array_equal(partial, partial.T)
        assert (np.diag(partial) == 0).all()
        assert np.array_equal(partial != 0, truth.adjacency)
        assert np.allclose(np.diag(truth.correlation), 1.0)
        # partial correlations recovered from the implied correlation matrix equal P
        k = np.linalg.inv(truth.correlation)
        d = np.sqrt(np.diag(k))
        implied = -k / np.outer(d, d)
        np.fill_diagonal(implied, 0.0)
        assert np.allclose(implied, partial, atol=1e-8)
        assert 0.0 < truth.shrinkage <= 1.0


def test_make_truth_is_deterministic() -> None:
    first = make_truth("clustered", 20, np.random.default_rng(7))
    second = make_truth("clustered", 20, np.random.default_rng(7))

    assert first.truth_hash == second.truth_hash
    assert np.array_equal(first.partial_correlations, second.partial_correlations)


def test_random_sparse_density() -> None:
    rng = np.random.default_rng(0)
    densities = [np.triu(erdos_renyi(30, 0.20, rng), 1).sum() / (30 * 29 / 2) for _ in range(500)]

    assert np.mean(densities) == pytest.approx(0.20, abs=0.02)


def test_isolates_have_empty_rows() -> None:
    rng = np.random.default_rng(1)
    for _ in range(50):
        truth = make_truth("random_with_isolates", 20, rng)
        isolated = ~truth.adjacency.any(axis=1)
        assert isolated.sum() >= 5  # 25% of 20 are isolated by construction (others may be too, by chance)
        assert (truth.partial_correlations[isolated] == 0).all()


def test_watts_strogatz_preserves_edge_count() -> None:
    rng = np.random.default_rng(2)
    for p in (10, 20, 30):
        lattice = watts_strogatz(p, 4, 0.0, rng)
        rewired = watts_strogatz(p, 4, 0.5, rng)
        assert np.triu(lattice, 1).sum() == p * 4 // 2
        assert np.triu(rewired, 1).sum() == p * 4 // 2
        assert np.array_equal(rewired, rewired.T) and not np.diag(rewired).any()


def test_stochastic_block_is_denser_within_blocks() -> None:
    rng = np.random.default_rng(3)
    adjacency = sum(stochastic_block(30, 6, 0.6, 0.05, rng).astype(int) for _ in range(200)) / 200
    labels = np.repeat(np.arange(6), 5)
    same = (labels[:, None] == labels[None, :]) & ~np.eye(30, dtype=bool)

    assert adjacency[same].mean() == pytest.approx(0.6, abs=0.03)
    assert adjacency[~same & ~np.eye(30, dtype=bool)].mean() == pytest.approx(0.05, abs=0.01)


def test_sampled_data_recovers_the_truth_correlation() -> None:
    truth = make_truth("random_dense", 10, np.random.default_rng(4))

    data = sample_data(truth, 200_000, np.random.default_rng(5))

    assert np.allclose(np.corrcoef(data, rowvar=False), truth.correlation, atol=0.02)


@pytest.mark.parametrize("bad", [("nonsense", 10), ("random_sparse", 3), ("random_sparse", 10.5)])
def test_invalid_arguments_raise(bad: tuple[str, float]) -> None:
    with pytest.raises(ValueError):
        make_truth(bad[0], bad[1], np.random.default_rng(0))  # type: ignore[arg-type]
