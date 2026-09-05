"""Generic aggregator for any sharded experiment run. See
.github/workflows/sharded_benchmark.yml -- that workflow and this
script work on any runner module that opts into the shard-aggregation
contract, not just `mintnet.experiments.stage5a` (its first user).

Contract a shardable module must expose (see stage5a.py's own "Generic
shard-aggregation contract" comment for the reference implementation):
    - `load_config(path) -> Config`
    - `expected_row_count(config) -> int`
    - `expected_combinations(config) -> set[tuple]`
    - `COMBINATION_COLUMNS: tuple[str, ...]`
plus a `<module>_reporting` companion module exposing
`write_report(raw, config, output_dir)`.

Each shard is one runner invocation restricted to a subset of cells
(`--no-report`, since a partial run's report would be misleading) that
wrote its own `raw_metrics.csv`. This script concatenates every shard's
raw metrics, verifies full coverage (every expected combination present
exactly once, no shard missing or duplicated), and only then calls the
module's own report writer -- producing the same report an unsharded
run would, since a well-behaved shardable runner derives its seeds from
the *full* grid's index, not the shard's own subset (see
`mintnet.experiments.stage5a.run_stage5a`'s own docstring, and its test
`test_stage5a_sharded_run_matches_unsharded_run`).
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from types import ModuleType

import pandas as pd


def _load_module(module_path: str) -> tuple[ModuleType, ModuleType]:
    runner = importlib.import_module(module_path)
    reporting = importlib.import_module(f"{module_path}_reporting")
    return runner, reporting


def aggregate(module_path: str, config_path: Path, shards_dir: Path, output_dir: Path) -> pd.DataFrame:
    runner, reporting = _load_module(module_path)
    config = runner.load_config(config_path)

    shard_paths = sorted(shards_dir.glob("*/raw_metrics.csv"))
    if not shard_paths:
        raise SystemExit(f"no raw_metrics.csv files found under {shards_dir}")

    raw = pd.concat((pd.read_csv(path) for path in shard_paths), ignore_index=True)

    expected_rows = runner.expected_row_count(config)
    if len(raw) != expected_rows:
        raise SystemExit(
            f"aggregated {len(raw)} rows from {len(shard_paths)} shard(s), expected {expected_rows} "
            "-- a shard is missing or duplicated"
        )

    combination_columns = list(runner.COMBINATION_COLUMNS)
    combos = set(raw[combination_columns].itertuples(index=False, name=None))
    expected_combos = runner.expected_combinations(config)
    if combos != expected_combos:
        missing = expected_combos - combos
        raise SystemExit(f"aggregated shards do not cover every combination -- missing: {missing}")

    dedup_columns = combination_columns + (["replicate"] if "replicate" in raw.columns else [])
    duplicate_keys = raw.duplicated(subset=dedup_columns)
    if duplicate_keys.any():
        raise SystemExit(f"{int(duplicate_keys.sum())} duplicate rows across shards (key: {dedup_columns})")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    reporting.write_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module", required=True,
        help="import path of the shardable runner module, e.g. mintnet.experiments.stage5a",
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--shards-dir", required=True, type=Path,
        help="directory containing one subdirectory per shard, each with its own raw_metrics.csv",
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    aggregate(arguments.module, arguments.config, arguments.shards_dir, arguments.output)


if __name__ == "__main__":
    main()
