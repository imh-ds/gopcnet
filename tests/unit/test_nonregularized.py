import numpy as np
import pytest

from gopcnet.comparators.nonregularized import _holm, fit_nonregularized_ggm, fit_nonregularized_ggm_from_correlation
from gopcnet.dpi.correlation_based import partial_correlation_test_from_corr


def _network_data(n: int, p: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    weights = np.triu(rng.uniform(0.15, 0.35, size=(p, p)) * (rng.random((p, p)) < 0.3), k=1)
    weights = weights + weights.T
    precision = np.eye(p) - weights
    shift = max(0.0, 0.2 - np.linalg.eigvalsh(precision).min())
    covariance = np.linalg.inv(precision + shift * np.eye(p))
    return rng.standard_normal((n, p)) @ np.linalg.cholesky(covariance).T


def test_full_order_values_match_the_conditional_test_given_all_others() -> None:
    data = _network_data(500, 7, seed=0)
    corr = np.corrcoef(data, rowvar=False)

    result = fit_nonregularized_ggm(data, correction="none")

    for i in range(7):
        for j in range(i + 1, 7):
            others = [k for k in range(7) if k not in (i, j)]
            reference = partial_correlation_test_from_corr(corr, 500, i, j, others)
            assert result.partial_correlations[i, j] == pytest.approx(reference.partial_correlation, abs=1e-10)
            assert result.p_values[i, j] == pytest.approx(reference.p_value, rel=1e-8, abs=1e-15)


def test_holm_step_down_on_hand_computed_example() -> None:
    # m = 4: thresholds .05/4, .05/3, .05/2, .05/1 = .0125, .0167, .025, .05
    p_values = np.array([0.010, 0.020, 0.015, 0.040])
    # sorted: .010 <= .0125, .015 <= .0167, .020 <= .025, .040 <= .05 -> all kept
    assert _holm(p_values, 0.05).tolist() == [True, True, True, True]
    # a failure stops the procedure even if later p-values would pass on their own
    p_values = np.array([0.010, 0.030, 0.016, 0.040])
    # sorted: .010 keep, .016 keep (<= .0167), .030 fails (> .025) -> stop
    assert _holm(p_values, 0.05).tolist() == [True, False, True, False]


def test_bh_is_less_conservative_than_holm() -> None:
    data = _network_data(400, 10, seed=1)

    holm = fit_nonregularized_ggm(data, correction="holm")
    bh = fit_nonregularized_ggm(data, correction="bh")
    none = fit_nonregularized_ggm(data, correction="none")

    assert not (holm.adjacency & ~bh.adjacency).any()
    assert not (bh.adjacency & ~none.adjacency).any()


def test_outputs_are_symmetric_and_weights_zero_off_support() -> None:
    result = fit_nonregularized_ggm(_network_data(300, 6, seed=2), correction="bh")

    assert np.array_equal(result.adjacency, result.adjacency.T)
    assert not np.diag(result.adjacency).any()
    assert np.allclose(result.weights, result.weights.T)
    assert (result.weights[~result.adjacency] == 0.0).all()


def test_holm_controls_familywise_error_under_the_null() -> None:
    rng = np.random.default_rng(3)
    trials = 300
    any_false_edge = sum(fit_nonregularized_ggm(rng.normal(size=(500, 10))).adjacency.any() for _ in range(trials))

    rate = any_false_edge / trials
    assert rate <= 0.05 + 3 * np.sqrt(0.05 * 0.95 / trials)


@pytest.mark.parametrize(
    "kwargs",
    [{"n": 7}, {"alpha": 0.0}, {"correction": "bonferroni"}, {"se_scale": 0.0}],  # p = 6: n must exceed 7
)
def test_invalid_arguments_raise(kwargs: dict) -> None:
    arguments = {"corr": np.eye(6), "n": 100}
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        fit_nonregularized_ggm_from_correlation(**arguments)


def test_singular_correlation_raises() -> None:
    corr = np.ones((3, 3))
    with pytest.raises(ValueError, match="singular"):
        fit_nonregularized_ggm_from_correlation(corr, 100)
