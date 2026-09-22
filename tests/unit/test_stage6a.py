from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gopcnet.experiments import stage6a
from gopcnet.experiments.stage6a_reporting import (
    _grid_summary,
    _safe_nanmean,
    compute_g1,
    compute_q3,
)
from gopcnet.simulation import bridges

CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "stage6a_smoke.yaml"


def _tiny_config() -> stage6a.Stage6aConfig:
    config = stage6a.load_stage6a_config(CONFIG_PATH)
    return replace(
        config,
        rho_bridge_grid=(0.08,),
        rho_confound_grid=(0.40,),
        sample_sizes=(1000,),
        replicates=4,
        development_replicates=(0, 1),
        validation_replicates=(2, 3),
        bootstrap_replicates=2,
        bootstrap_resamples=10,
    )


# --- simulation.bridges -----------------------------------------------------


def test_all_shapes_positive_definite_across_full_grid():
    rho_bridges = (0.05, 0.08, 0.12, 0.18)
    rho_confounds = (0.20, 0.30, 0.40)
    for name in bridges.SHAPE_NAMES:
        bridge_grid = rho_bridges if bridges.USES_BRIDGE_GRID[name] else (0.0,)
        for rho_bridge in bridge_grid:
            for rho_confound in rho_confounds:
                shape = bridges.make_shape(name, rho_bridge, rho_confound)
                cov = bridges.build_shape_covariance(shape)
                assert cov.shape == (shape.p, shape.p)


def test_confound_trap_latent_drops_only_the_confound_column():
    observed_shape = bridges.make_shape("confound_trap_observed", 0.08, 0.30)
    latent_shape = bridges.make_shape("confound_trap_latent", 0.08, 0.30)
    assert observed_shape.observed == tuple(range(7))
    assert latent_shape.observed == (0, 1, 2, 3, 4, 5)
    assert bridges.observed_true_bridges(latent_shape) == ((0, 3),)


def test_no_bridge_shape_has_no_true_bridges():
    shape = bridges.make_shape("no_bridge_negative_control", 0.08, 0.30)
    assert shape.true_bridges == ()
    assert len(shape.candidates) == 9


def test_double_bridge_has_two_true_bridges():
    shape = bridges.make_shape("double_bridge", 0.08, 0.30)
    assert set(shape.true_bridges) == {(0, 3), (1, 4)}


def test_sample_shape_standardizes_columns():
    shape = bridges.make_shape("confound_trap_observed", 0.08, 0.30)
    data = bridges.sample_shape(shape, 500, np.random.default_rng(0))
    assert data.shape == (500, 7)
    assert np.allclose(data.mean(axis=0), 0, atol=1e-8)
    assert np.allclose(data.std(axis=0, ddof=1), 1, atol=1e-8)


# --- stage6a runner ----------------------------------------------------------


def test_cells_for_skips_bridge_grid_for_negative_control():
    config = stage6a.load_stage6a_config(CONFIG_PATH)
    cells = stage6a.cells_for(replace(config, shapes=("no_bridge_negative_control",)))
    rho_bridges = {cell[1] for cell in cells}
    assert rho_bridges == {0.0}


def test_expected_row_count_matches_candidate_counts():
    config = _tiny_config()
    combos = stage6a.expected_combinations(replace(config, shapes=("confound_trap_observed",)))
    # 1 rho_bridge x 1 rho_confound x 1 N x 4 replicates x 9 candidate pairs
    assert len(combos) == 1 * 1 * 1 * 4 * 9


def test_run_produces_expected_rows_and_is_deterministic(tmp_path):
    config = _tiny_config()
    first = stage6a.run_stage6a(config, tmp_path / "a", max_workers=1, shapes=("confound_trap_observed",), write_report=False)
    second = stage6a.run_stage6a(config, tmp_path / "b", max_workers=1, shapes=("confound_trap_observed",), write_report=False)
    assert (first["status"] == "ok").all()
    assert len(first) == 4 * 9
    pd.testing.assert_frame_equal(first, second)


def test_sharded_run_matches_unsharded(tmp_path):
    config = replace(_tiny_config(), sample_sizes=(500, 1000))
    full = stage6a.run_stage6a(config, tmp_path / "full", max_workers=1, shapes=("confound_trap_observed",), write_report=False)
    shard = stage6a.run_stage6a(
        config, tmp_path / "shard", max_workers=1, shapes=("confound_trap_observed",), sample_sizes=(1000,), write_report=False
    )
    keys = ["shape", "n", "replicate", "seed", "pair", "marg", "surv", "maxp"]
    expected = full[full["n"] == 1000][keys].reset_index(drop=True)
    pd.testing.assert_frame_equal(expected, shard[keys].reset_index(drop=True))


def test_true_bridge_survives_conditioning_more_than_screened_out_decoy(tmp_path):
    """Sanity check on the statistic itself, not just plumbing: on a
    strongly-signalled cell, the true bridge's survival fraction should
    typically exceed that of at least one decoy pair."""
    config = replace(_tiny_config(), rho_bridge_grid=(0.18,), rho_confound_grid=(0.20,), replicates=8)
    raw = stage6a.run_stage6a(config, tmp_path, max_workers=1, shapes=("confound_trap_observed",), write_report=False)
    bridge_rows = raw[raw["is_true_bridge"]]
    decoy_rows = raw[~raw["is_true_bridge"]]
    assert bridge_rows["surv"].mean() >= decoy_rows["surv"].mean()


def test_unknown_shape_rejected():
    with pytest.raises(ValueError):
        bridges.make_shape("not_a_real_shape", 0.08, 0.30)


# --- reporting ---------------------------------------------------------------


def test_safe_nanmean_handles_all_nan():
    assert np.isnan(_safe_nanmean([float("nan"), float("nan")]))
    assert np.isnan(_safe_nanmean([]))
    assert _safe_nanmean([1.0, float("nan"), 3.0]) == pytest.approx(2.0)


def test_g1_agrees_when_scores_are_identical():
    rows = []
    for replicate in range(3):
        for pair, surv, maxp in (("0-3", 1.0, 0.001), ("1-4", 0.5, 0.4)):
            rows.append(
                dict(shape="confound_trap_observed", rho_bridge=0.08, rho_confound=0.30, n=1000, replicate=replicate, pair=pair, surv=surv, maxp=maxp)
            )
    validation = pd.DataFrame(rows)
    result = compute_g1(validation)
    assert result["passed"] is True
    assert result["mean_agreement_fraction"] == 1.0


def test_grid_summary_reports_nan_recovery_for_no_bridge_shape():
    rows = []
    for replicate in range(2):
        for pair in ("0-3", "0-4", "0-5"):
            rows.append(
                dict(
                    shape="no_bridge_negative_control", rho_bridge=0.0, rho_confound=0.30, n=1000, replicate=replicate,
                    pair=pair, marg=0.05, surv=0.0, maxp=1.0, screened_out=True,
                )
            )
    validation = pd.DataFrame(rows)
    grid = _grid_summary(validation)
    assert len(grid) == 1
    assert np.isnan(grid.iloc[0]["recovery_surv"])
    assert grid.iloc[0]["false_confirm_rate"] == 0.0


def test_q3_flags_flat_vs_shrinking_false_confirm_rate():
    grid = pd.DataFrame(
        [
            {"shape": "confound_trap_observed", "n": 500, "false_confirm_rate": 0.03},
            {"shape": "confound_trap_observed", "n": 3000, "false_confirm_rate": 0.005},
            {"shape": "confound_trap_latent", "n": 500, "false_confirm_rate": 0.14},
            {"shape": "confound_trap_latent", "n": 3000, "false_confirm_rate": 0.13},
        ]
    )
    result = compute_q3(grid)
    assert "confirms the disclosed limitation" in result["verdict"]
