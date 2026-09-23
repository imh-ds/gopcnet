from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gopcnet.experiments import stage7a
from gopcnet.experiments.stage7a import (
    Stage7aConfig,
    cells_for,
    expected_combinations,
    expected_row_count,
    load_stage7a_config,
    run_stage7a,
    run_with_budget,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _tiny_config() -> Stage7aConfig:
    base = load_stage7a_config(REPOSITORY_ROOT / "configs/stage7a_engine_smoke.yaml")
    return replace(
        base,
        part_a_dgps=("triangle_balanced", "chain_fork_hub"),
        part_a_sample_sizes=(750, 1000),
        part_a_replicates=4,
        development_replicates=(0, 1),
        validation_replicates=(2, 3),
        part_b_structures=("random_sparse",),
        part_b_ps=(10,),
        part_b_replicates=2,
    )


def test_configs_load_and_match_the_charter_grid() -> None:
    full = load_stage7a_config(REPOSITORY_ROOT / "configs/stage7a_engine.yaml")
    smoke = load_stage7a_config(REPOSITORY_ROOT / "configs/stage7a_engine_smoke.yaml")

    assert full.part_a_replicates == 1000 and full.validation_replicates == (500, 999)
    assert full.part_b_ps == (10, 20, 30) and full.part_b_n == 500 and full.component_budget_seconds == 60
    assert expected_row_count(full) == 20 * 1000 * 5 + 9 * 20 * 2
    for field in ("part_a_dgps", "part_a_sample_sizes", "part_b_structures", "part_b_ps", "master_seed"):
        assert getattr(full, field) == getattr(smoke, field)


def test_end_to_end_run_writes_complete_evidence_and_report(tmp_path: Path) -> None:
    config = _tiny_config()

    raw = run_stage7a(config, tmp_path, max_workers=2)

    assert len(raw) == expected_row_count(config)
    assert set(raw[list(stage7a.COMBINATION_COLUMNS)].itertuples(index=False, name=None)) == expected_combinations(
        config
    )
    assert (raw["status"] == "ok").all(), raw.loc[raw["status"] != "ok", "error"].tolist()
    for name in ("raw_metrics.csv", "resolved_config.yaml", "metadata.json", "report.json", "stage7a_report.md"):
        assert (tmp_path / name).is_file()
    report = (tmp_path / "stage7a_report.md").read_text(encoding="utf-8")
    assert "G1" in report and "Q1" in report and "Q3" in report


def test_sharded_run_matches_unsharded(tmp_path: Path) -> None:
    config = replace(_tiny_config(), part_b_structures=(), part_b_ps=())
    whole = run_stage7a(config, tmp_path / "whole", max_workers=1, write_report=False)
    shards = [
        run_stage7a(config, tmp_path / f"s{k}", max_workers=1, names=(name,), levels=(level,), write_report=False)
        for k, (name, level) in enumerate([(c.name, c.level) for c in cells_for(config)])
    ]
    combined = pd.concat(shards, ignore_index=True)

    key = ["part", "name", "level", "method", "replicate"]
    left = whole.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    right = combined.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    pd.testing.assert_frame_equal(left, right)


def test_empty_shard_writes_header_only_csv(tmp_path: Path) -> None:
    raw = run_stage7a(_tiny_config(), tmp_path, names=("triangle_balanced",), levels=(30,))

    assert raw.empty
    written = pd.read_csv(tmp_path / "raw_metrics.csv")
    assert written.empty and list(written.columns) == list(stage7a.RAW_COLUMNS)


def test_budget_terminates_a_slow_fit() -> None:
    rng = np.random.default_rng(0)
    data = rng.standard_normal((300, 12)) + rng.standard_normal((300, 1))  # everything correlated

    status, payload, seconds = run_with_budget(data, {"screening_alpha": 0.001, "dpi_alpha": 0.2}, 0.001)

    assert status == "timeout" and payload is None


def test_budget_returns_the_fit_when_it_finishes() -> None:
    rng = np.random.default_rng(1)
    data = rng.normal(size=(200, 4))

    status, payload, seconds = run_with_budget(data, {"screening_alpha": 0.01, "dpi_alpha": 0.05}, 60)

    assert status == "ok"
    adjacency, _ = payload
    assert adjacency.shape == (4, 4) and seconds >= 0


def test_write_report_alias_exists() -> None:
    from gopcnet.experiments import stage7a_reporting

    assert stage7a_reporting.write_report is stage7a_reporting.write_stage7a_report


def test_self_check_passes() -> None:
    assert stage7a.self_check()["passed"]


@pytest.mark.parametrize("part", ["A", "B"])
def test_seeds_do_not_depend_on_shard_filters(part: str) -> None:
    config = _tiny_config()
    cell = next(c for c in cells_for(config) if c.part == part)
    filtered = [c for c in cells_for(config) if c.name == cell.name and c.level == cell.level][0]

    assert filtered == cell
    if part == "A":
        assert stage7a.part_a_seed(config, cell, 3) == stage7a.part_a_seed(config, filtered, 3)
    else:
        assert stage7a.part_b_seeds(config, cell, 1) == stage7a.part_b_seeds(config, filtered, 1)
