"""fit_gopc(engine="adjacency"): the PC-stable-restricted pruning engine
(docs/development_plan/phase1_external_validity.md, step 1.3)."""

import time
from itertools import combinations

import numpy as np
import pytest

from gopcnet import fit_gopc
from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected


def _chain(n: int, p: int, rho: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    columns = [rng.normal(size=n)]
    for _ in range(p - 1):
        columns.append(rho * columns[-1] + np.sqrt(1 - rho**2) * rng.normal(size=n))
    return np.column_stack(columns)


def _dense_network(n: int, p: int, density: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    weights = np.triu(rng.uniform(0.1, 0.3, size=(p, p)) * (rng.random((p, p)) < density), k=1)
    weights = weights + weights.T
    precision = np.eye(p) - weights
    shift = max(0.0, 0.1 - np.linalg.eigvalsh(precision).min())
    covariance = np.linalg.inv(precision + shift * np.eye(p))
    return rng.standard_normal((n, p)) @ np.linalg.cholesky(covariance).T


@pytest.mark.parametrize("data", [_chain(800, 3, 0.6, 0), np.random.default_rng(1).normal(size=(500, 4))])
def test_engines_agree_on_small_shapes(data: np.ndarray) -> None:
    component = fit_gopc(data, screening_alpha=0.01, dpi_alpha=0.05)
    adjacency = fit_gopc(data, screening_alpha=0.01, dpi_alpha=0.05, engine="adjacency")

    assert np.array_equal(component.adjacency, adjacency.adjacency)
    assert np.allclose(component.weights, adjacency.weights)


def test_zero_cap_returns_the_screened_graph() -> None:
    data = _dense_network(400, 8, 0.4, seed=2)
    screened = screen_uncorrected(compute_pairwise_screening_evidence(data), 0.001)

    result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.1, max_conditioning_size=0, engine="adjacency")

    assert np.array_equal(result.adjacency, screened)
    assert np.array_equal(result.diagnostics.screened, screened)
    assert result.diagnostics.n_tests.sum() == 0


def test_retained_edges_are_a_subset_of_the_screen() -> None:
    data = _dense_network(600, 12, 0.35, seed=3)

    result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.1, engine="adjacency")

    assert not (result.adjacency & ~result.diagnostics.screened).any()
    assert np.array_equal(result.adjacency, result.adjacency.T)
    assert (result.diagnostics.max_p_value[np.triu(result.adjacency, 1)] <= 0.1).all()


def _pcor(data: np.ndarray, i: int, j: int, subset: tuple[int, ...]) -> float:
    return compute_partial_correlation_evidence(data, i, j, list(subset)).partial_correlation


@pytest.mark.parametrize("seed", [4, 8, 9])
def test_weights_follow_the_d055_convention(seed: int) -> None:
    """D-055: the minimum-magnitude signed partial correlation over every
    tested set of size >= 1. Level 1 is searched on the screened graph
    itself (the neighbor snapshot before any pruning), so every level-1
    set is known exactly: the weight's magnitude must not exceed any of
    them, and the weight must be the partial correlation of *some* set
    drawn from an endpoint's screened neighborhood. An edge that was
    never conditioning-tested keeps its marginal correlation."""
    data = _dense_network(1500, 7, 0.45, seed=seed)
    result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.05, engine="adjacency")
    screened = result.diagnostics.screened

    for i, j in zip(*np.nonzero(np.triu(result.adjacency, 1))):
        i, j = int(i), int(j)
        pool_i = sorted(set(np.flatnonzero(screened[i])) - {j})
        pool_j = sorted(set(np.flatnonzero(screened[j])) - {i})
        level_one = [_pcor(data, i, j, (k,)) for k in sorted(set(pool_i) | set(pool_j))]
        if not level_one:
            assert result.weights[i, j] == pytest.approx(np.corrcoef(data[:, i], data[:, j])[0, 1])
            continue
        assert abs(result.weights[i, j]) <= min(abs(value) for value in level_one) + 1e-10
        candidates = [
            _pcor(data, i, j, subset)
            for pool in (pool_i, pool_j)
            for size in range(1, min(len(pool), 4) + 1)
            for subset in combinations(pool, size)
        ]
        assert min(abs(result.weights[i, j] - value) for value in candidates) < 1e-10


def test_adjacency_engine_scales_where_the_component_engine_does_not() -> None:
    """The review's probe: p = 20, dense, N = 300 took ~200 s with the
    component engine. The adjacency engine must stay well under that."""
    data = _dense_network(300, 20, 0.35, seed=5)

    started = time.perf_counter()
    fit_gopc(data, screening_alpha=0.001, dpi_alpha=0.2, engine="adjacency")

    assert time.perf_counter() - started < 10.0


def test_component_engine_has_no_diagnostics_and_is_the_default() -> None:
    data = _chain(500, 3, 0.6, seed=6)

    default = fit_gopc(data, screening_alpha=0.01, dpi_alpha=0.05)
    component = fit_gopc(data, screening_alpha=0.01, dpi_alpha=0.05, engine="component")

    assert default.diagnostics is None and component.diagnostics is None
    assert np.array_equal(default.adjacency, component.adjacency)


@pytest.mark.parametrize("kwargs", [{"engine": "pc"}, {"max_conditioning_size": -1}, {"max_conditioning_size": 1.5}])
def test_invalid_engine_arguments_raise(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        fit_gopc(_chain(200, 3, 0.5, seed=7), screening_alpha=0.01, dpi_alpha=0.05, **kwargs)
