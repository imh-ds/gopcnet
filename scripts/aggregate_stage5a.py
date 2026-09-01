"""Aggregate Stage 5a CI shard outputs into one combined evidence
directory and the final descriptive-verdict report. See
docs/stage5a_charter.md and .github/workflows/stage5a_benchmark.yml.

Each shard (one GitHub Actions matrix job, one (dgp, N) cell) writes
its own `raw_metrics.csv` via `mintnet.experiments.stage5a`'s own
`--no-report` mode. This script concatenates every shard's raw metrics,
verifies full coverage (every dgp/N/method/replicate cell present
exactly once), and only then runs the report -- the same report the
runner would produce for an unsharded run, byte-for-byte, since each
shard's seeds are derived from the full DGPS/sample_sizes index, not
the shard's own subset.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mintnet.experiments.stage5a import DGPS, METHODS, load_stage5a_config
from mintnet.experiments.stage5a_reporting import write_stage5a_report


def aggregate(config_path: Path, shards_dir: Path, output_dir: Path) -> pd.DataFrame:
    config = load_stage5a_config(config_path)
    shard_paths = sorted(shards_dir.glob("*/raw_metrics.csv"))
    if not shard_paths:
        raise SystemExit(f"no raw_metrics.csv files found under {shards_dir}")

    raw = pd.concat((pd.read_csv(path) for path in shard_paths), ignore_index=True)

    expected_rows = len(DGPS) * len(config.sample_sizes) * config.replicates * len(METHODS)
    if len(raw) != expected_rows:
        raise SystemExit(
            f"aggregated {len(raw)} rows from {len(shard_paths)} shard(s), expected {expected_rows} "
            f"({len(DGPS)} dgps x {len(config.sample_sizes)} sample sizes x {config.replicates} "
            f"replicates x {len(METHODS)} methods) -- a shard is missing or duplicated"
        )

    combos = set(zip(raw["dgp"], raw["n"], raw["method"]))
    expected_combos = {(d, n, m) for d in DGPS for n in config.sample_sizes for m in METHODS}
    if combos != expected_combos:
        missing = expected_combos - combos
        raise SystemExit(f"aggregated shards do not cover every (dgp, n, method) combination -- missing: {missing}")

    duplicate_keys = raw.duplicated(subset=["dgp", "n", "method", "replicate"])
    if duplicate_keys.any():
        raise SystemExit(f"{int(duplicate_keys.sum())} duplicate (dgp, n, method, replicate) rows across shards")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    write_stage5a_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--shards-dir", required=True, type=Path,
        help="directory containing one subdirectory per shard, each with its own raw_metrics.csv",
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    aggregate(arguments.config, arguments.shards_dir, arguments.output)


if __name__ == "__main__":
    main()
