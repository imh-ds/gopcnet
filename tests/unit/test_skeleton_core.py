import numpy as np
import pytest

from gopcnet.comparators.pc_skeleton import fit_pc_skeleton
from gopcnet.pipeline.skeleton_core import pc_stable_skeleton


def _chain_data(n: int, p: int, rho: float, rng: np.random.Generator) -> np.ndarray:
    columns = [rng.normal(size=n)]
    for _ in range(p - 1):
        columns.append(rho * columns[-1] + np.sqrt(1 - rho**2) * rng.normal(size=n))
    return np.column_stack(columns)


def _random_network_data(n: int, p: int, rng: np.random.Generator) -> np.ndarray:
    weights = np.triu(rng.uniform(0.15, 0.35, size=(p, p)) * (rng.random((p, p)) < 0.3), k=1)
    weights = weights + weights.T
    precision = np.eye(p) - weights
    shift = max(0.0, 0.2 - np.linalg.eigvalsh(precision).min())
    covariance = np.linalg.inv(precision + shift * np.eye(p))
    return rng.standard_normal((n, p)) @ np.linalg.cholesky(covariance).T


@pytest.mark.parametrize("p", [5, 8, 12])
@pytest.mark.parametrize("n", [100, 500])
def test_complete_start_equals_frozen_pc(p: int, n: int) -> None:
    """From the complete graph, level 0, unbounded, the core is PC-stable
    and must reproduce the frozen comparator exactly (a tie within 1e-9
    of alpha is the only tolerated source of disagreement)."""
    rng = np.random.default_rng(1000 * p + n)
    for replicate in range(17):
        if replicate % 3 == 0:
            data = rng.normal(size=(n, p))
        elif replicate % 3 == 1:
            data = _chain_data(n, p, 0.5, rng)
        else:
            data = _random_network_data(n, p, rng)
        corr = np.corrcoef(data, rowvar=False)

        core = pc_stable_skeleton(corr, n, 0.01)
        frozen = fit_pc_skeleton(data, alpha=0.01)

        mismatch = core.adjacency != frozen.adjacency
        if mismatch.any():
            i, j = np.argwhere(np.triu(mismatch))[0]
            assert abs(core.max_p_value[i, j] - 0.01) < 1e-9, f"real mismatch at {(i, j)}"


def test_chain_separating_set_is_the_middle_node() -> None:
    data = _chain_data(3000, 3, 0.6, np.random.default_rng(0))

    core = pc_stable_skeleton(np.corrcoef(data, rowvar=False), 3000, 0.01)

    assert not core.adjacency[0, 2]
    assert core.separating_set[(0, 2)] == (1,)
    assert core.adjacency[0, 1] and core.adjacency[1, 2]


def test_max_level_bounds_the_search() -> None:
    data = _random_network_data(400, 10, np.random.default_rng(1))
    corr = np.corrcoef(data, rowvar=False)

    core = pc_stable_skeleton(corr, 400, 0.05, max_level=1)

    assert core.level_reached <= 1
    assert all(len(subset) <= 1 for subset in core.separating_set.values())
    # every pair tested at most once per level-0 set plus C(p-2, 1) level-1 sets
    assert core.n_tests.max() <= 1 + 2 * (10 - 2)


def test_start_adjacency_edges_are_never_added() -> None:
    data = _chain_data(500, 4, 0.6, np.random.default_rng(2))
    start = np.ones((4, 4), dtype=bool)
    np.fill_diagonal(start, False)
    start[0, 1] = start[1, 0] = False  # a real edge, deliberately withheld

    core = pc_stable_skeleton(np.corrcoef(data, rowvar=False), 500, 0.01, start_adjacency=start, start_level=1)

    assert not core.adjacency[0, 1]
    assert not (core.adjacency & ~start).any()


def test_start_level_one_skips_marginal_tests() -> None:
    data = np.random.default_rng(3).normal(size=(300, 4))  # independent: level 0 would remove everything

    core = pc_stable_skeleton(np.corrcoef(data, rowvar=False), 300, 0.01, start_level=1, max_level=1)

    assert all(len(subset) == 1 for subset in core.separating_set.values())


def test_outputs_are_symmetric_and_retained_edges_have_small_max_p() -> None:
    data = _random_network_data(600, 9, np.random.default_rng(4))

    core = pc_stable_skeleton(np.corrcoef(data, rowvar=False), 600, 0.05, max_level=4)

    for array in (core.adjacency, core.n_tests, core.cap_reached):
        assert np.array_equal(array, array.T)
    for array in (core.max_p_value, core.min_abs_partial):
        assert np.array_equal(np.isnan(array), np.isnan(array.T))
        assert np.allclose(np.nan_to_num(array), np.nan_to_num(array.T))
    retained = np.triu(core.adjacency, k=1)
    assert (core.max_p_value[retained] <= 0.05).all()
    removed_pairs = list(core.separating_set)
    assert all(core.max_p_value[i, j] > 0.05 for i, j in removed_pairs)
    assert not core.cap_reached[~core.adjacency].any()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"corr": np.ones((2, 3)), "n": 100, "alpha": 0.05},
        {"corr": np.eye(3), "n": 3, "alpha": 0.05},
        {"corr": np.eye(3), "n": 100, "alpha": 1.0},
        {"corr": np.array([[1.0, 0.2], [0.3, 1.0]]), "n": 100, "alpha": 0.05},
    ],
)
def test_invalid_input_raises(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        pc_stable_skeleton(**kwargs)
