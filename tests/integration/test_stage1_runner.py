from pathlib import Path

import pandas as pd

from mintnet.experiments.stage1 import load_stage1_config, run_stage1


def test_stage1_smoke_runner_is_deterministic(tmp_path: Path) -> None:
    """Changing Stage 1 seed derivation must change neither raw evidence run."""
    config = load_stage1_config(Path("configs/stage1_dpi_smoke.yaml"))

    first = run_stage1(config, tmp_path / "first")
    second = run_stage1(config, tmp_path / "second")

    assert len(first) == 3 * 1 * 1 * 2 * len(config.taus)
    pd.testing.assert_frame_equal(
        first.drop(columns="elapsed_seconds"), second.drop(columns="elapsed_seconds")
    )
    for output in (tmp_path / "first", tmp_path / "second"):
        for filename in (
            "raw_metrics.csv",
            "resolved_config.yaml",
            "metadata.json",
        ):
            assert (output / filename).is_file()
