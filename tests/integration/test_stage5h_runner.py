import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from mintnet.experiments.stage5h import DGPS, METHODS, load_stage5h_config, run_stage5h


def test_stage5h_smoke_runner_is_deterministic(tmp_path: Path) -> None:
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    first = run_stage5h(config, tmp_path / "first")
    second = run_stage5h(config, tmp_path / "second")

    expected_rows = len(DGPS) * len(config.sample_sizes) * len(config.strengths) * config.replicates * len(METHODS)
    assert len(first) == expected_rows
    pd.testing.assert_frame_equal(
        first.drop(columns="elapsed_seconds"), second.drop(columns="elapsed_seconds")
    )
    for output in (tmp_path / "first", tmp_path / "second"):
        for filename in ("raw_metrics.csv", "resolved_config.yaml", "metadata.json", "stage5h_report.md"):
            assert (output / filename).is_file()


def test_stage5h_covers_every_dgp_n_strength_method_combination(tmp_path: Path) -> None:
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    raw = run_stage5h(config, tmp_path / "evidence")

    combos = set(zip(raw["dgp"], raw["n"], raw["strength"], raw["method"]))
    expected = {(d, n, s, meth) for d in DGPS for n in config.sample_sizes for s in config.strengths for meth in METHODS}
    assert combos == expected


def test_stage5h_metrics_are_well_formed(tmp_path: Path) -> None:
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    raw = run_stage5h(config, tmp_path / "evidence")

    ok = raw.loc[raw["status"] == "ok"]
    assert not ok.empty
    for col in ("precision", "recall", "f1"):
        valid = ok[col].dropna()
        assert (valid >= 0.0).all() and (valid <= 1.0).all()
    assert (ok["shd"] >= 0.0).all()


def test_stage5h_pc_alpha_is_fixed_and_n_independent(tmp_path: Path) -> None:
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    raw = run_stage5h(config, tmp_path / "evidence")

    pc = raw.loc[(raw["method"] == "pc") & (raw["status"] == "ok")]
    assert not pc.empty
    assert pc["pc_alpha"].sub(0.01).abs().max() < 1e-12


def test_stage5h_screening_alpha_matches_native_p_exactly(tmp_path: Path) -> None:
    """At the native noise multiplier, p=15 for both shapes, so
    alpha(p) must equal D-047's own original .001 exactly -- shared by
    both GOPC variants (mint, gopc_growing_subset)."""
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    raw = run_stage5h(config, tmp_path / "evidence")

    for method in ("mint", "gopc_growing_subset"):
        rows = raw.loc[(raw["method"] == method) & (raw["status"] == "ok")]
        assert (rows["p"] == 15).all()
        assert rows["screening_alpha"].sub(0.001).abs().max() < 1e-12


def test_stage5h_seeds_are_disjoint_from_stage5d(tmp_path: Path) -> None:
    from mintnet.experiments.stage5d import _condition_seed as stage5d_seed
    from mintnet.experiments.stage5h import _condition_seed as stage5h_seed

    for dgp_index in range(2):
        for sample_index in range(2):
            for replicate in range(2):
                assert stage5d_seed(20260830, dgp_index, sample_index, 0, replicate) != stage5h_seed(
                    20260830, dgp_index, sample_index, 0, replicate
                )


def test_stage5h_sample_sizes_exclude_n_500() -> None:
    """docs/stage5h_charter.md's own reason for existing: N=500 falls
    outside GOPC's pruning significance level's validated range and
    must not appear in this charter's own default config."""
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way.yaml"))

    assert 500 not in config.sample_sizes
    assert set(config.sample_sizes) == {750, 1000, 1500, 1750}


def test_stage5h_three_dimensions_are_independently_shardable(tmp_path: Path) -> None:
    config = load_stage5h_config(Path("configs/stage5h_strength_sweep_four_way_smoke.yaml"))

    unsharded = run_stage5h(config, tmp_path / "unsharded")
    shard = run_stage5h(
        config, tmp_path / "shard",
        dgps=("chain_fork_hub",), sample_sizes=(750,), strengths=(0.3,), write_report=False,
    )

    expected = unsharded.loc[
        (unsharded["dgp"] == "chain_fork_hub") & (unsharded["n"] == 750) & (unsharded["strength"] == 0.3)
    ].reset_index(drop=True)
    actual = shard.reset_index(drop=True)
    pd.testing.assert_frame_equal(expected.drop(columns="elapsed_seconds"), actual.drop(columns="elapsed_seconds"))
    assert not (tmp_path / "shard" / "stage5h_report.md").exists()


def test_stage5h_aggregate_shards_reproduces_unsharded_report(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, "scripts")
    from aggregate_shards import aggregate

    config_path = Path("configs/stage5h_strength_sweep_four_way_smoke.yaml")
    config = load_stage5h_config(config_path)

    unsharded_dir = tmp_path / "unsharded"
    unsharded = run_stage5h(config, unsharded_dir)

    shards_dir = tmp_path / "shards"
    for dgp in DGPS:
        for n in config.sample_sizes:
            run_stage5h(
                config, shards_dir / f"{dgp}_{n}",
                dgps=(dgp,), sample_sizes=(n,), strengths=config.strengths, write_report=False,
            )

    aggregated_dir = tmp_path / "aggregated"
    aggregated = aggregate("mintnet.experiments.stage5h", config_path, shards_dir, aggregated_dir)

    key = ["dgp", "n", "strength", "method", "replicate"]
    unsharded_sorted = unsharded.sort_values(key).reset_index(drop=True)
    aggregated_sorted = aggregated.sort_values(key).reset_index(drop=True)
    unsharded_sorted["error"] = unsharded_sorted["error"].replace("", pd.NA).fillna("")
    aggregated_sorted["error"] = aggregated_sorted["error"].fillna("")
    pd.testing.assert_frame_equal(
        unsharded_sorted.drop(columns="elapsed_seconds"),
        aggregated_sorted.drop(columns="elapsed_seconds"),
        check_dtype=False,
    )
    for filename in ("raw_metrics.csv", "report.json", "stage5h_report.md", "precision_by_strength.png"):
        assert (aggregated_dir / filename).is_file()


def test_stage5h_provenance_records_charter_hash(tmp_path: Path, monkeypatch) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config = load_stage5h_config(
        (repository_root / "configs/stage5h_strength_sweep_four_way_smoke.yaml").resolve()
    )
    output = (tmp_path / "evidence").resolve()
    expected_hash = hashlib.sha256((repository_root / "docs/stage5h_charter.md").read_bytes()).hexdigest()
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository_root, text=True).strip()

    monkeypatch.chdir(tmp_path)
    run_stage5h(config, output)

    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["charter_sha256"] == expected_hash
    assert metadata["git_commit"] == expected_commit
