import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

from mintnet.experiments.stage5a import DGPS, METHODS, load_stage5a_config, run_stage5a


def test_stage5a_smoke_runner_is_deterministic(tmp_path: Path) -> None:
    config = load_stage5a_config(Path("configs/stage5a_comparator_benchmark_smoke.yaml"))

    first = run_stage5a(config, tmp_path / "first")
    second = run_stage5a(config, tmp_path / "second")

    expected_rows = len(DGPS) * len(config.sample_sizes) * config.replicates * len(METHODS)
    assert len(first) == expected_rows
    pd.testing.assert_frame_equal(
        first.drop(columns="elapsed_seconds"), second.drop(columns="elapsed_seconds")
    )
    for output in (tmp_path / "first", tmp_path / "second"):
        for filename in ("raw_metrics.csv", "resolved_config.yaml", "metadata.json", "stage5a_report.md"):
            assert (output / filename).is_file()


def test_stage5a_covers_every_dgp_n_method_combination(tmp_path: Path) -> None:
    config = load_stage5a_config(Path("configs/stage5a_comparator_benchmark_smoke.yaml"))

    raw = run_stage5a(config, tmp_path / "evidence")

    combos = set(zip(raw["dgp"], raw["n"], raw["method"]))
    expected = {(d, n, m) for d in DGPS for n in config.sample_sizes for m in METHODS}
    assert combos == expected


def test_stage5a_both_methods_see_identical_underlying_draw(tmp_path: Path) -> None:
    """Paired same-draw design: both methods must be fit on identical data
    at each (dgp, N, replicate), since the draw depends only on seed."""
    config = load_stage5a_config(Path("configs/stage5a_comparator_benchmark_smoke.yaml"))

    raw = run_stage5a(config, tmp_path / "evidence")

    for dgp in DGPS:
        for n in config.sample_sizes:
            cell = raw.loc[(raw["dgp"] == dgp) & (raw["n"] == n)]
            seeds_by_method = cell.groupby("method")["seed"].apply(lambda s: tuple(sorted(s)))
            assert seeds_by_method.nunique() == 1


def test_stage5a_metrics_are_well_formed(tmp_path: Path) -> None:
    config = load_stage5a_config(Path("configs/stage5a_comparator_benchmark_smoke.yaml"))

    raw = run_stage5a(config, tmp_path / "evidence")

    ok = raw.loc[raw["status"] == "ok"]
    assert not ok.empty
    for col in ("precision", "recall", "f1"):
        valid = ok[col].dropna()
        assert (valid >= 0.0).all() and (valid <= 1.0).all()
    assert (ok["shd"] >= 0.0).all()


def test_stage5a_seeds_are_disjoint_from_stage4p(tmp_path: Path) -> None:
    """Stage 5a's own seed derivation adds a stage tag disjoint from
    every prior charter's own SeedSequence entropy (docs/stage5a_charter.md's
    own seed requirement)."""
    from mintnet.experiments.stage4p import _condition_seed as stage4p_seed
    from mintnet.experiments.stage5a import _condition_seed as stage5a_seed

    for dgp_index in range(2):
        for sample_index in range(2):
            for replicate in range(2):
                assert stage4p_seed(20260830, dgp_index, sample_index, replicate) != stage5a_seed(
                    20260830, dgp_index, sample_index, replicate
                )


def test_stage5a_provenance_records_charter_hash(tmp_path: Path, monkeypatch) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config = load_stage5a_config(
        (repository_root / "configs/stage5a_comparator_benchmark_smoke.yaml").resolve()
    )
    output = (tmp_path / "evidence").resolve()
    expected_hash = hashlib.sha256((repository_root / "docs/stage5a_charter.md").read_bytes()).hexdigest()
    expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository_root, text=True).strip()

    monkeypatch.chdir(tmp_path)
    run_stage5a(config, output)

    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["charter_sha256"] == expected_hash
    assert metadata["git_commit"] == expected_commit
