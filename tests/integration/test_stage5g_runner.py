import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from mintnet.experiments.stage5a import DGPS, _DGP_REGISTRY, _condition_seed as stage5a_seed
from mintnet.experiments.stage5g import METHODS, load_stage5g_config, run_stage5g


def test_stage5g_smoke_runner_is_deterministic(tmp_path: Path) -> None:
    config = load_stage5g_config(Path("configs/stage5g_growing_subset_smoke.yaml"))

    first = run_stage5g(config, tmp_path / "first")
    second = run_stage5g(config, tmp_path / "second")

    expected_rows = len(DGPS) * len(config.sample_sizes) * config.replicates * len(METHODS)
    assert len(first) == expected_rows
    pd.testing.assert_frame_equal(
        first.drop(columns="elapsed_seconds"), second.drop(columns="elapsed_seconds")
    )
    for output in (tmp_path / "first", tmp_path / "second"):
        for filename in ("raw_metrics.csv", "resolved_config.yaml", "metadata.json", "stage5g_report.md"):
            assert (output / filename).is_file()


def test_stage5g_covers_every_dgp_n_method_combination(tmp_path: Path) -> None:
    config = load_stage5g_config(Path("configs/stage5g_growing_subset_smoke.yaml"))

    raw = run_stage5g(config, tmp_path / "evidence")

    combos = set(zip(raw["dgp"], raw["n"], raw["method"]))
    expected = {(d, n, m) for d in DGPS for n in config.sample_sizes for m in METHODS}
    assert combos == expected


def test_stage5g_metrics_are_well_formed(tmp_path: Path) -> None:
    config = load_stage5g_config(Path("configs/stage5g_growing_subset_smoke.yaml"))

    raw = run_stage5g(config, tmp_path / "evidence")

    ok = raw.loc[raw["status"] == "ok"]
    assert not ok.empty
    for col in ("precision", "recall", "f1"):
        valid = ok[col].dropna()
        assert (valid >= 0.0).all() and (valid <= 1.0).all()
    assert (ok["shd"] >= 0.0).all()


def test_stage5g_seeds_are_bit_identical_to_stage5a() -> None:
    """Only a paired comparison against D-047/D-051 if this charter
    draws literally the same data -- docs/stage5g_charter.md's own
    paired-comparison design, load-bearing."""
    from mintnet.experiments.stage5g import _condition_seed as stage5g_seed

    assert stage5g_seed is stage5a_seed
    for dgp_index in range(3):
        for sample_index in range(3):
            for replicate in range(3):
                assert stage5g_seed(20260830, dgp_index, sample_index, replicate) == stage5a_seed(
                    20260830, dgp_index, sample_index, replicate
                )


def test_stage5g_dgp_registry_matches_stage5a() -> None:
    from mintnet.experiments.stage5g import _DGP_REGISTRY as stage5g_registry

    assert stage5g_registry is _DGP_REGISTRY


def test_stage5g_sharded_run_matches_unsharded_run(tmp_path: Path) -> None:
    config = load_stage5g_config(Path("configs/stage5g_growing_subset_smoke.yaml"))

    unsharded = run_stage5g(config, tmp_path / "unsharded")
    shard = run_stage5g(
        config, tmp_path / "shard", dgps=("chain_fork_hub",), sample_sizes=(750,), write_report=False
    )

    expected = unsharded.loc[unsharded["dgp"] == "chain_fork_hub"].reset_index(drop=True)
    actual = shard.reset_index(drop=True)
    pd.testing.assert_frame_equal(expected.drop(columns="elapsed_seconds"), actual.drop(columns="elapsed_seconds"))
    assert not (tmp_path / "shard" / "stage5g_report.md").exists()


def test_stage5g_aggregate_shards_reproduces_unsharded_report(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, "scripts")
    from aggregate_shards import aggregate

    config_path = Path("configs/stage5g_growing_subset_smoke.yaml")
    config = load_stage5g_config(config_path)

    unsharded_dir = tmp_path / "unsharded"
    unsharded = run_stage5g(config, unsharded_dir)

    shards_dir = tmp_path / "shards"
    for dgp in DGPS:
        run_stage5g(
            config, shards_dir / dgp, dgps=(dgp,), sample_sizes=config.sample_sizes, write_report=False
        )

    aggregated_dir = tmp_path / "aggregated"
    aggregated = aggregate("mintnet.experiments.stage5g", config_path, shards_dir, aggregated_dir)

    unsharded_sorted = unsharded.sort_values(["dgp", "n", "method", "replicate"]).reset_index(drop=True)
    aggregated_sorted = aggregated.sort_values(["dgp", "n", "method", "replicate"]).reset_index(drop=True)
    unsharded_sorted["error"] = unsharded_sorted["error"].replace("", pd.NA).fillna("")
    aggregated_sorted["error"] = aggregated_sorted["error"].fillna("")
    pd.testing.assert_frame_equal(
        unsharded_sorted.drop(columns="elapsed_seconds"),
        aggregated_sorted.drop(columns="elapsed_seconds"),
        check_dtype=False,
    )
    for filename in ("raw_metrics.csv", "report.json", "stage5g_report.md"):
        assert (aggregated_dir / filename).is_file()


def test_stage5g_provenance_records_charter_hash(tmp_path: Path, monkeypatch) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config = load_stage5g_config(
        (repository_root / "configs/stage5g_growing_subset_smoke.yaml").resolve()
    )
    output = (tmp_path / "evidence").resolve()
    expected_hash = hashlib.sha256((repository_root / "docs/stage5g_charter.md").read_bytes()).hexdigest()
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository_root, text=True).strip()

    monkeypatch.chdir(tmp_path)
    run_stage5g(config, output)

    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["charter_sha256"] == expected_hash
    assert metadata["git_commit"] == expected_commit
