import warnings
from pathlib import Path

import numpy as np
import pytest
import yaml

from gopcnet import fit_gopc, fit_gopc_fixed_order
from gopcnet.defaults import (
    _DPI_INTERCEPT,
    _DPI_LOG_SLOPE,
    OutsideValidatedRangeWarning,
    ResolvedAlphas,
    default_dpi_alpha,
    default_screening_alpha,
    resolve_alphas,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_dpi_constants_are_d012_fit_at_full_precision() -> None:
    from gopcnet.experiments.stage1j_fit import fit_candidate_forms, select_form

    form = select_form(fit_candidate_forms())

    assert form.name == "linear_log_n"
    assert form.parameters == pytest.approx((_DPI_INTERCEPT, _DPI_LOG_SLOPE), rel=0, abs=1e-15)


def test_default_dpi_alpha_matches_archived_stage5i_values() -> None:
    """Ties the shipped default to the alpha(N) values the archived
    Stage 5i evidence was actually produced with."""
    resolved = yaml.safe_load(
        (REPOSITORY_ROOT / "evidence/stage5_benchmarks/stage5i_pc_alpha_sweep/resolved_config.yaml").read_text(
            encoding="utf-8"
        )
    )
    archived = resolved["d012_alpha_by_n"]
    assert set(archived) == {750, 1000, 1500, 1750}

    for n, alpha in archived.items():
        assert default_dpi_alpha(n) == pytest.approx(alpha, rel=0, abs=1e-12)


def test_default_screening_alpha_anchors_clamp_and_interpolation() -> None:
    from gopcnet.experiments.stage5c import _screening_alpha_for_p

    assert default_screening_alpha(15) == 0.001
    assert default_screening_alpha(30) == pytest.approx(0.0001, rel=1e-12)
    for p in (3, 8, 14):
        assert default_screening_alpha(p) == 0.001  # clamp: raw interpolation would rise here
    for p in (15, 16, 20, 24, 27):
        assert default_screening_alpha(p) == pytest.approx(_screening_alpha_for_p(p), rel=1e-12)


@pytest.mark.parametrize("n", [300, 699, 3001, 5000])
def test_dpi_default_warns_outside_validated_n(n: int) -> None:
    with pytest.warns(OutsideValidatedRangeWarning, match="extrapolated"):
        default_dpi_alpha(n)


def test_dpi_default_warns_in_thin_margin_band() -> None:
    with pytest.warns(OutsideValidatedRangeWarning, match="recommended floor"):
        default_dpi_alpha(720)


def test_dpi_default_clips_at_very_large_n() -> None:
    with pytest.warns(OutsideValidatedRangeWarning, match="clipped"):
        assert default_dpi_alpha(50_000) == pytest.approx(1e-4)


@pytest.mark.parametrize("p", [2, 31, 40])
def test_screening_default_warns_outside_validated_p(p: int) -> None:
    with pytest.warns(OutsideValidatedRangeWarning):
        default_screening_alpha(p)


def test_no_warning_inside_validated_range() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        resolved = resolve_alphas(1000, 15)
        default_dpi_alpha(750)
        default_screening_alpha(30)

    assert resolved == ResolvedAlphas(
        screening_alpha=0.001,
        dpi_alpha=default_dpi_alpha(1000),
        screening_source="default",
        dpi_source="default",
        warnings=(),
    )


def test_user_values_are_used_as_given_and_never_range_checked() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        resolved = resolve_alphas(50, 60, screening_alpha=np.float32(0.01), dpi_alpha=0.05)

    assert resolved.screening_alpha == pytest.approx(0.01)
    assert resolved.dpi_alpha == 0.05
    assert (resolved.screening_source, resolved.dpi_source) == ("user", "user")


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5, True, "0.05"])
def test_invalid_user_alpha_raises(bad: object) -> None:
    with pytest.raises(ValueError):
        resolve_alphas(1000, 15, screening_alpha=bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        resolve_alphas(1000, 15, dpi_alpha=bad)  # type: ignore[arg-type]


def test_screening_looser_than_pruning_warns_but_does_not_raise() -> None:
    with pytest.warns(UserWarning, match="stricter test"):
        resolved = resolve_alphas(1000, 15, screening_alpha=0.2, dpi_alpha=0.05)
    assert resolved.screening_alpha == 0.2


@pytest.mark.parametrize("bad", [(3, 15), (1000, 1), (1000.5, 15)])
def test_invalid_n_or_p_raises(bad: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        resolve_alphas(*bad)  # type: ignore[arg-type]


# --- fit_gopc / fit_gopc_fixed_order integration ------------------------


def _chain_data(n: int, p: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    columns = [rng.normal(size=n)]
    for _ in range(p - 1):
        columns.append(0.5 * columns[-1] + np.sqrt(1 - 0.25) * rng.normal(size=n))
    return np.column_stack(columns)


@pytest.mark.parametrize("fit", [fit_gopc, fit_gopc_fixed_order])
def test_explicit_alpha_outputs_match_pre_defaults_regression_fixture(fit) -> None:
    """Explicit-alpha calls must be bit-identical to the pre-defaults
    implementation: every archived result depends on it. The fixture was
    generated from commit 0708f6e (before `gopcnet.defaults` existed)."""
    fixture = np.load(REPOSITORY_ROOT / "tests/fixtures/gopc_explicit_alpha_regression.npz")
    prefix = "growing" if fit is fit_gopc else "fixed"

    for k in range(3):
        result = fit(fixture[f"data_{k}"], screening_alpha=0.001, dpi_alpha=0.13)
        assert np.array_equal(result.adjacency, fixture[f"{prefix}_adjacency_{k}"])
        assert np.array_equal(result.weights, fixture[f"{prefix}_weights_{k}"])


@pytest.mark.parametrize("fit", [fit_gopc, fit_gopc_fixed_order])
def test_defaults_equal_explicit_default_values(fit) -> None:
    data = _chain_data(1000, 15, seed=3)

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # N = 1000, p = 15: inside the validated range
        by_default = fit(data)
    explicit = fit(data, screening_alpha=0.001, dpi_alpha=default_dpi_alpha(1000))

    assert np.array_equal(by_default.adjacency, explicit.adjacency)
    assert np.array_equal(by_default.weights, explicit.weights)
    assert by_default.screening_alpha == 0.001
    assert by_default.dpi_alpha == default_dpi_alpha(1000)


def test_fit_gopc_records_user_alphas() -> None:
    result = fit_gopc(_chain_data(300, 4, seed=4), screening_alpha=0.01, dpi_alpha=0.05)

    assert (result.screening_alpha, result.dpi_alpha) == (0.01, 0.05)


def test_fit_gopc_warning_points_at_the_caller() -> None:
    with pytest.warns(OutsideValidatedRangeWarning) as record:
        fit_gopc(_chain_data(300, 4, seed=5))

    assert all(Path(w.filename).resolve() == Path(__file__).resolve() for w in record)


def test_fit_gopc_rejects_non_two_dimensional_data() -> None:
    with pytest.raises(ValueError, match="two-dimensional"):
        fit_gopc(np.zeros(10))
