from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gopcnet.experiments import stage7b
from gopcnet.experiments.stage7b import (
    ANCHOR,
    Stage7bConfig,
    cells_for,
    data_seed,
    expected_combinations,
    expected_row_count,
    load_stage7b_config,
    run_stage7b,
    structure_metrics,
    truth_seed,
)
from gopcnet.experiments.stage7b_reporting import _trend, routing

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _tiny() -> Stage7bConfig:
    base = load_stage7b_config(REPOSITORY_ROOT / "configs/stage7b_external_validity_smoke.yaml")
    return replace(
        base,
        structures=("random_sparse",),
        ps=(10,),
        sample_sizes=(250, 500),
        replicates=4,
        development_replicates=(0, 1),
        validation_replicates=(2, 3),
        anchor_sample_sizes=(1000,),
        g1_subsample_replicates=2,
    )


def test_full_and_smoke_configs_share_the_grid() -> None:
    full = load_stage7b_config(REPOSITORY_ROOT / "configs/stage7b_external_validity.yaml")
    smoke = load_stage7b_config(REPOSITORY_ROOT / "configs/stage7b_external_validity_smoke.yaml")

    for field in ("structures", "ps", "sample_sizes", "pc_alphas", "gopc_engine", "anchor_sample_sizes", "master_seed"):
        assert getattr(full, field) == getattr(smoke, field)
    assert len(cells_for(full)) == 5 * 3 * 4 + 2


def test_end_to_end_run_is_complete_and_reports(tmp_path: Path) -> None:
    config = _tiny()

    raw = run_stage7b(config, tmp_path, max_workers=2)

    assert len(raw) == expected_row_count(config)
    combos = set(raw[list(stage7b.COMBINATION_COLUMNS)].itertuples(index=False, name=None))
    assert combos == expected_combinations(config)
    assert (raw["status"] == "ok").all(), raw.loc[raw["status"] != "ok", ["method", "error"]].to_dict("records")
    gopc = raw[raw["method"] == "gopc"]
    assert gopc["screen_pass_fraction"].notna().all() and gopc["weight_mae_refit"].notna().all()
    assert raw.loc[raw["method"] == "pc@0.01", "weight_mae_native"].isna().all()  # PC has no native weights
    assert (raw.loc[raw["structure"] == ANCHOR, "method"] == stage7b.ANCHOR_METHOD).all()
    for name in ("raw_metrics.csv", "resolved_config.yaml", "metadata.json", "report.json", "stage7b_report.md"):
        assert (tmp_path / name).is_file()


def test_truth_is_paired_across_n_and_data_is_not() -> None:
    config = _tiny()
    small, large = [c for c in cells_for(config) if c.structure == "random_sparse"]

    assert truth_seed(config, small, 1) == truth_seed(config, large, 1)
    assert data_seed(config, small, 1) != data_seed(config, large, 1)


def test_anchor_seeds_equal_stage5a_archive_seeds() -> None:
    config = _tiny()
    anchor = next(c for c in cells_for(config) if c.structure == ANCHOR)
    archive = pd.read_csv(REPOSITORY_ROOT / "evidence/stage5_benchmarks/stage5g_growing_subset/raw_metrics.csv")
    archived = archive[(archive["dgp"] == "chain_fork_hub") & (archive["n"] == 1000) & (archive["replicate"] < 3)]

    from gopcnet.experiments.stage5a import _condition_seed

    ours = [_condition_seed(20260830, 0, anchor.n_index, r) for r in range(3)]
    assert ours == archived.sort_values("replicate")["seed"].tolist()


def test_sharded_run_matches_unsharded(tmp_path: Path) -> None:
    config = replace(_tiny(), anchor_sample_sizes=())
    whole = run_stage7b(config, tmp_path / "whole", max_workers=1, write_report=False)
    shards = pd.concat(
        [run_stage7b(config, tmp_path / str(n), max_workers=1, sample_sizes=(n,), write_report=False) for n in (250, 500)],
        ignore_index=True,
    )
    key = ["structure", "p", "n", "method", "replicate"]
    left = whole.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    right = shards.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    pd.testing.assert_frame_equal(left, right)


def test_cell_and_replicate_block_sharding_matches_unsharded(tmp_path: Path) -> None:
    """The plan used for the full run: `--cells` x `--replicate-blocks`."""
    config = replace(_tiny(), structures=("random_sparse", "clustered"))
    whole = run_stage7b(config, tmp_path / "whole", max_workers=1, write_report=False)
    shards = [
        run_stage7b(config, tmp_path / f"{token}_{block}", max_workers=1, write_report=False,
                    cells=(token,), replicate_block=stage7b.parse_replicate_block(block))  # fmt: skip
        for token in stage7b.cell_tokens(config)
        for block in ("0-1", "2-3")
    ]
    combined = pd.concat(shards, ignore_index=True)

    assert len(combined) == expected_row_count(config)
    key = ["structure", "p", "n", "method", "replicate"]
    left = whole.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    right = combined.sort_values(key).reset_index(drop=True).drop(columns="elapsed_seconds")
    pd.testing.assert_frame_equal(left, right)


def test_cell_tokens_and_block_parsing() -> None:
    full = load_stage7b_config(REPOSITORY_ROOT / "configs/stage7b_external_validity.yaml")

    tokens = stage7b.cell_tokens(full)
    assert len(tokens) == 5 * 3 + 1 and "random_dense-p30" in tokens and f"{ANCHOR}-p15" in tokens
    assert all(":" not in token for token in tokens)  # GitHub artifact names reject ':'
    assert stage7b.parse_replicate_block("50-99") == range(50, 100)
    with pytest.raises(ValueError):
        stage7b.parse_replicate_block("9-3")


def test_empty_shard_writes_header_only_csv(tmp_path: Path) -> None:
    raw = run_stage7b(_tiny(), tmp_path, structures=(ANCHOR,), ps=(10,))

    assert raw.empty
    assert list(pd.read_csv(tmp_path / "raw_metrics.csv").columns) == list(stage7b.RAW_COLUMNS)


def test_structure_metrics_on_a_hand_example() -> None:
    truth = np.zeros((4, 4), dtype=bool)
    truth[0, 1] = truth[1, 0] = truth[2, 3] = truth[3, 2] = True
    estimated = np.zeros((4, 4), dtype=bool)
    estimated[0, 1] = estimated[1, 0] = estimated[0, 2] = estimated[2, 0] = True

    m = structure_metrics(estimated, truth)  # TP 1, FP 1, FN 1, TN 3

    assert (m["sensitivity"], m["specificity"], m["precision"]) == (0.5, 0.75, 0.5)
    assert m["mcc"] == pytest.approx((1 * 3 - 1 * 1) / np.sqrt(2 * 2 * 4 * 4))


@pytest.mark.parametrize(
    "values, expected",
    [([0.5, 0.6, 0.7], "increasing"), ([0.9, 0.8, 0.6], "decreasing"), ([0.8, 0.805, 0.8], "flat"), ([0.5, 0.9, 0.4], "non-monotone")],
)
def test_trend_classification(values: list[float], expected: str) -> None:
    assert _trend(values) == expected


def _q2(verdicts: dict[str, str]) -> dict:
    return {"verdicts": {s: {"verdict": v} for s, v in verdicts.items()}}


def _q3(worse: dict[str, int]) -> dict:
    return {"counts": {s: {"nonreg_holm": {"worse": k, "comparable": 9 - k}, "nonreg_bh": {"comparable": 9}} for s, k in worse.items()}}


def test_routing_branches() -> None:
    structures = ["random_sparse", "random_dense", "small_world", "clustered", "random_with_isolates"]
    none_worse = _q3({s: 0 for s in structures})
    assert routing(_q2({s: "HOLDS" for s in structures}), none_worse) == "A"
    assert routing(_q2({s: "HOLDS" for s in structures}), _q3({s: 6 for s in structures})) == "C"
    assert routing(_q2({s: "FAILS" for s in structures}), none_worse) == "D"
    noise_only = {s: "FAILS" for s in structures[:4]} | {"random_with_isolates": "HOLDS"}
    assert routing(_q2(noise_only), none_worse) == "B"


def test_write_report_alias_exists() -> None:
    from gopcnet.experiments import stage7b_reporting

    assert stage7b_reporting.write_report is stage7b_reporting.write_stage7b_report
