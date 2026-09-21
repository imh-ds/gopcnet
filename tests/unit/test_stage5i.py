from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gopcnet.experiments import stage5i
from gopcnet.experiments.stage5i_reporting import (
    _bootstrap_ci,
    _select_alpha,
    predicted_weak_edge_recall,
)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "stage5i_smoke.yaml"


def _tiny_config() -> stage5i.Stage5iConfig:
    config = stage5i.load_stage5i_config(CONFIG_PATH)
    return replace(config, sample_sizes=(750,), replicates=2, development_replicates=(0, 0), validation_replicates=(1, 1))


def test_method_list_matches_charter():
    assert len(stage5i.METHODS) == 13
    assert len(set(stage5i.METHODS)) == 13
    assert "pc@0.01" in stage5i.METHODS and "gopc_growing@validated" in stage5i.METHODS
    assert {"pc@0.0125", "pc@0.125", "gopc_matched@0.01", "gopc_matched@0.1"} <= set(stage5i.METHODS)


def test_edge_encoding_round_trips():
    rng = np.random.default_rng(0)
    for p in (3, 15):
        upper = rng.random((p, p)) < 0.4
        adjacency = np.triu(upper, 1)
        adjacency = adjacency | adjacency.T
        rows, cols = np.triu_indices(p, k=1)
        decoded = stage5i.decode_edges(stage5i.encode_edges(adjacency), p)
        assert np.array_equal(decoded, adjacency[rows, cols])


def test_empty_and_full_graphs_encode():
    assert stage5i.encode_edges(np.zeros((3, 3), dtype=bool)) == "0x0"
    full = ~np.eye(3, dtype=bool)
    assert stage5i.decode_edges(stage5i.encode_edges(full), 3).all()


def test_expected_row_count_and_combinations():
    config = stage5i.load_stage5i_config(CONFIG_PATH)
    assert stage5i.expected_row_count(config) == 5 * 4 * 20 * 13
    assert len(stage5i.expected_combinations(config)) == 5 * 4 * 13


def test_seeds_use_stage5a_full_grid_indices():
    """Every sample size must be present in Stage 5a's seven-value grid so
    sample_index (hence every seed) matches the archived draws."""
    config = stage5i.load_stage5i_config(CONFIG_PATH)
    assert set(config.sample_sizes) <= set(stage5i.STAGE5A_SAMPLE_SIZES)
    assert stage5i.STAGE5A_SAMPLE_SIZES.index(1750) == 6


def test_predicted_recall_matches_charter_table():
    assert predicted_weak_edge_recall(0.08, 1750, 0.01) == pytest.approx(0.927, abs=0.001)
    assert predicted_weak_edge_recall(0.08, 1750, 0.09964) == pytest.approx(0.985, abs=0.001)
    assert predicted_weak_edge_recall(0.12, 750, 0.01) == pytest.approx(0.921, abs=0.001)


def test_select_alpha_breaks_ties_toward_smaller_alpha():
    scores = pd.Series({0.05: 0.9, 0.001: 0.9, 0.01: 0.9, 0.1: 0.8})
    assert _select_alpha(scores) == 0.001
    assert _select_alpha(pd.Series({0.001: 0.5, 0.2: 0.7})) == 0.2


def test_bootstrap_ci_contains_mean():
    rng = np.random.default_rng(1)
    mean, low, high = _bootstrap_ci(np.array([0.0, 0.1, 0.2, 0.1, 0.0, 0.3]), rng)
    assert low <= mean <= high


def test_run_produces_all_methods_and_is_deterministic(tmp_path):
    config = _tiny_config()
    first = stage5i.run_stage5i(
        config, tmp_path / "a", max_workers=1, dgps=("triangle_strong",), write_report=False
    )
    second = stage5i.run_stage5i(
        config, tmp_path / "b", max_workers=1, dgps=("triangle_strong",), write_report=False
    )
    assert set(first["method"]) == set(stage5i.METHODS)
    assert len(first) == 2 * len(stage5i.METHODS)
    assert (first["status"] == "ok").all()
    pd.testing.assert_frame_equal(
        first.drop(columns="elapsed_seconds"), second.drop(columns="elapsed_seconds")
    )
    assert (tmp_path / "a" / "raw_metrics.csv").is_file()


def test_sharded_run_matches_unsharded(tmp_path):
    config = replace(_tiny_config(), sample_sizes=(750, 1000))
    full = stage5i.run_stage5i(
        config, tmp_path / "full", max_workers=1, dgps=("triangle_moderate",), write_report=False
    )
    shard = stage5i.run_stage5i(
        config, tmp_path / "shard", max_workers=1, dgps=("triangle_moderate",), sample_sizes=(1000,), write_report=False
    )
    keys = ["dgp", "n", "method", "replicate", "seed", "n_estimated_edges"]
    expected = full[full["n"] == 1000][keys].reset_index(drop=True)
    pd.testing.assert_frame_equal(expected, shard[keys].reset_index(drop=True))


def test_unknown_sample_size_rejected(tmp_path):
    config = replace(_tiny_config(), sample_sizes=(800,))
    with pytest.raises(ValueError, match="Stage 5a's grid"):
        stage5i.run_stage5i(config, tmp_path, max_workers=1, write_report=False)


def test_encoded_edges_survive_csv_round_trip(tmp_path):
    adjacency = np.zeros((15, 15), dtype=bool)
    adjacency[0, 3] = adjacency[3, 0] = True  # bit pattern that reads as "1e..." without a prefix
    encoded = stage5i.encode_edges(adjacency)
    path = tmp_path / "x.csv"
    pd.DataFrame({"edge_bits": [encoded, "0x0"]}).to_csv(path, index=False)
    back = pd.read_csv(path)["edge_bits"].tolist()
    assert back == [encoded, "0x0"]
    assert np.array_equal(stage5i.decode_edges(back[0], 15), stage5i.decode_edges(encoded, 15))
