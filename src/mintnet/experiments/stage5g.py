"""Deterministic raw-evidence runner for the frozen Stage 5g
growing-subset-DPI comparison. See docs/stage5g_charter.md.

Runs only the new growing-subset-DPI variant of GOPC's own pruning
step (`mintnet.pipeline.growing_subset_dpi.growing_subset_dpi`) --
GOPC-original and PC are not re-run here; their numbers are D-047's and
D-051's own, loaded from `evidence/stage5_benchmarks/` and referenced
in the report, not regenerated. This charter reuses Stage 5a's own DGP
registry, full grid, and exact condition-seed derivation
(`stage5a._condition_seed`, unchanged `_STAGE_TAG`/`master_seed`) so
every `(dgp, N, replicate)` cell draws the identical simulated dataset
D-047 and D-051 were computed on -- a three-way paired comparison, not
merely a comparable one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml

from mintnet.experiments.stage1j_fit import fit_candidate_forms, select_form
from mintnet.experiments.stage5a import DGPS, _DGP_REGISTRY, _condition_seed, _graph_metrics, _true_adjacency
from mintnet.pipeline import growing_subset_dpi
from mintnet.screening import compute_pairwise_screening_evidence, screen_uncorrected

METHODS: tuple[str, ...] = ("gopc_growing_subset",)


@dataclass(frozen=True)
class Stage5gConfig:
    sample_sizes: tuple[int, ...]
    strength: float
    screening_alpha: float
    max_conditioning_size: int
    replicates: int
    master_seed: int
    development_replicates: tuple[int, int]
    validation_replicates: tuple[int, int]
    source_path: Path | None = None


def load_stage5g_config(path: Path) -> Stage5gConfig:
    with path.open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise ValueError("Stage 5g configuration must be a mapping")
    return Stage5gConfig(
        sample_sizes=tuple(int(v) for v in values["sample_sizes"]),
        strength=float(values["strength"]),
        screening_alpha=float(values["screening_alpha"]),
        max_conditioning_size=int(values["max_conditioning_size"]),
        replicates=int(values["replicates"]),
        master_seed=int(values["master_seed"]),
        development_replicates=tuple(int(v) for v in values["development_replicates"]),
        validation_replicates=tuple(int(v) for v in values["validation_replicates"]),
        source_path=path.resolve(),
    )


# --- Generic shard-aggregation contract -------------------------------
# See stage5a.py's own comment for the full contract description.

load_config = load_stage5g_config
COMBINATION_COLUMNS: tuple[str, ...] = ("dgp", "n", "method")


def expected_row_count(config: Stage5gConfig) -> int:
    return len(DGPS) * len(config.sample_sizes) * config.replicates * len(METHODS)


def expected_combinations(config: Stage5gConfig) -> set[tuple[str, int, str]]:
    return {(dgp, n, method) for dgp in DGPS for n in config.sample_sizes for method in METHODS}


def _repository_root(config: Stage5gConfig) -> Path:
    if config.source_path is not None:
        return config.source_path.parent.parent
    return Path(__file__).resolve().parents[3]


def _git_commit(repository_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _resolved_config(config: Stage5gConfig, alpha_by_n: dict[int, float]) -> dict[str, object]:
    return {
        "sample_sizes": list(config.sample_sizes),
        "strength": config.strength,
        "screening_alpha": config.screening_alpha,
        "max_conditioning_size": config.max_conditioning_size,
        "replicates": config.replicates,
        "master_seed": config.master_seed,
        "development_replicates": list(config.development_replicates),
        "validation_replicates": list(config.validation_replicates),
        "d012_alpha_by_n": alpha_by_n,
        "note": (
            "master_seed/strength/screening_alpha are unchanged from stage5a_comparator_benchmark.yaml "
            "so this charter's condition seeds and screened candidate graphs are bit-identical to D-047's "
            "and D-051's own draws -- see docs/stage5g_charter.md's paired-comparison design."
        ),
    }


def _write_evidence(
    config: Stage5gConfig, output_dir: Path, raw: pd.DataFrame, alpha_by_n: dict[int, float], runtime_seconds: float
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_resolved_config(config, alpha_by_n), stream, sort_keys=True)

    repository_root = _repository_root(config)
    charter = repository_root / "docs/stage5g_charter.md"
    charter_hash = hashlib.sha256(charter.read_bytes()).hexdigest() if charter.is_file() else None
    metadata = {
        "charter_sha256": charter_hash,
        "git_commit": _git_commit(repository_root),
        "python": sys.version,
        "platform": platform.platform(),
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "runtime_seconds": runtime_seconds,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _growing_subset_adjacency(
    data: np.ndarray, screening_alpha: float, dpi_alpha: float, max_conditioning_size: int
) -> np.ndarray:
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, screening_alpha)
    result = growing_subset_dpi(data, screened, dpi_alpha, max_conditioning_size=max_conditioning_size)
    return result.adjacency


def _run_cell(task: tuple[int, str, int, int, float, Stage5gConfig]) -> list[dict[str, object]]:
    """Every (dgp, N) cell's full replicate loop, self-contained and
    picklable so it can run in a worker process. Seeds are derived via
    `stage5a._condition_seed` unchanged -- identical draws to D-047/D-051."""
    dgp_index, dgp_name, sample_index, n, dpi_alpha, config = task
    dgp = _DGP_REGISTRY[dgp_name]
    sample: Callable = dgp["sample"]  # type: ignore[assignment]
    p = int(dgp["p"])
    truth = _true_adjacency(dgp["true_edges"], p)  # type: ignore[arg-type]

    rows: list[dict[str, object]] = []
    for replicate in range(config.replicates):
        seed = _condition_seed(config.master_seed, dgp_index, sample_index, replicate)
        try:
            data = sample(n, config.strength, np.random.default_rng(seed))
            status, error = "ok", ""
        except Exception as exc:
            data = None
            status, error = "error", f"{type(exc).__name__}: {exc}"

        for method in METHODS:
            started = time.perf_counter()
            row_status, row_error = status, error
            metrics: dict[str, object] = {
                "precision": np.nan,
                "recall": np.nan,
                "f1": np.nan,
                "shd": np.nan,
                "n_estimated_edges": np.nan,
            }
            if data is not None:
                try:
                    estimated = _growing_subset_adjacency(
                        data, config.screening_alpha, dpi_alpha, config.max_conditioning_size
                    )
                    metrics = _graph_metrics(estimated, truth)
                except Exception as exc:
                    row_status = "error"
                    row_error = f"{type(exc).__name__}: {exc}"

            rows.append(
                {
                    "dgp": dgp_name,
                    "method": method,
                    "n": n,
                    "alpha": dpi_alpha,
                    "replicate": replicate,
                    "seed": seed,
                    **metrics,
                    "elapsed_seconds": time.perf_counter() - started,
                    "status": row_status,
                    "error": row_error,
                }
            )
    return rows


def run_stage5g(
    config: Stage5gConfig,
    output_dir: Path,
    max_workers: int | None = None,
    dgps: tuple[str, ...] | None = None,
    sample_sizes: tuple[int, ...] | None = None,
    write_report: bool = True,
) -> pd.DataFrame:
    """Run growing-subset DPI across all five DGP shapes and the full N
    grid, on data drawn identically to D-047/D-051's own. See stage5e's
    own docstring for the sharding-filter contract this mirrors."""
    import os
    from concurrent.futures import ProcessPoolExecutor

    run_started = time.perf_counter()

    selected = select_form(fit_candidate_forms())
    alpha_by_n = {n: selected.predict(float(n)) for n in config.sample_sizes}

    target_dgps = set(dgps) if dgps is not None else set(DGPS)
    target_sizes = set(sample_sizes) if sample_sizes is not None else set(config.sample_sizes)

    tasks = [
        (dgp_index, dgp_name, sample_index, n, alpha_by_n[n], config)
        for dgp_index, dgp_name in enumerate(DGPS)
        if dgp_name in target_dgps
        for sample_index, n in enumerate(config.sample_sizes)
        if n in target_sizes
    ]
    if not tasks:
        raise ValueError("dgps/sample_sizes filter selected no cells")

    if max_workers is None:
        max_workers = min(len(tasks), max(1, (os.cpu_count() or 1) - 1))

    rows: list[dict[str, object]] = []
    if max_workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for cell_rows in executor.map(_run_cell, tasks):
                rows.extend(cell_rows)
    else:
        for task in tasks:
            rows.extend(_run_cell(task))

    raw = pd.DataFrame(rows)
    _write_evidence(config, output_dir, raw, alpha_by_n, time.perf_counter() - run_started)
    if not write_report:
        return raw
    from mintnet.experiments.stage5g_reporting import write_stage5g_report

    write_stage5g_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--dgps", type=str, default=None, help="comma-separated subset of DGP shapes to run (default: all)"
    )
    parser.add_argument(
        "--sample-sizes", type=str, default=None, help="comma-separated subset of N values to run (default: all)"
    )
    parser.add_argument(
        "--no-report", action="store_true", help="skip the descriptive-verdict report (use for CI shards)"
    )
    arguments = parser.parse_args()
    dgps = tuple(arguments.dgps.split(",")) if arguments.dgps else None
    sample_sizes = tuple(int(value) for value in arguments.sample_sizes.split(",")) if arguments.sample_sizes else None
    run_stage5g(
        load_stage5g_config(arguments.config),
        arguments.output,
        max_workers=arguments.workers,
        dgps=dgps,
        sample_sizes=sample_sizes,
        write_report=not arguments.no_report,
    )


if __name__ == "__main__":
    main()
