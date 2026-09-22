"""Deterministic raw-evidence runner for the frozen Stage 6a
edge-evidence-tier / cross-community bridge-inference validation
charter. See docs/stage6a_charter.md.

For every candidate cross-cluster pair in every (shape, rho_bridge,
rho_confound, N, replicate) cell, computes three ranking scores from the
same fitted candidate graph and per-set p-values: raw marginal
correlation (the naive baseline this charter argues against), the
survival fraction across every tested conditioning-set size 0..
max_conditioning_size (this charter's candidate addition), and a
PC-"pMax"-style score (the largest p-value seen across every tested set,
an existing PC diagnostic, included so novelty is scoped correctly).

Uses the package's own existing statistical primitive
(`gopcnet.dpi.multi_conditional.compute_partial_correlation_evidence`) --
no new test. Uses a fresh, disjoint seed tag (506): this charter's shapes
are new DGPs, not a re-use of any prior charter's own draws.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence
from gopcnet.experiments.stage1j_fit import fit_candidate_forms, select_form
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected
from gopcnet.simulation.bridges import (
    SHAPE_NAMES,
    USES_BRIDGE_GRID,
    build_shape_covariance,
    make_shape,
    observed_candidates,
    observed_true_bridges,
    sample_shape,
)

_STAGE_TAG = 506  # disjoint from every prior charter's own seed derivation; new DGPs, not reused draws


@dataclass(frozen=True)
class Stage6aConfig:
    shapes: tuple[str, ...]
    rho_bridge_grid: tuple[float, ...]
    rho_confound_grid: tuple[float, ...]
    sample_sizes: tuple[int, ...]
    screening_alpha: float
    max_conditioning_size: int
    replicates: int
    master_seed: int
    development_replicates: tuple[int, int]
    validation_replicates: tuple[int, int]
    bootstrap_replicates: int
    bootstrap_resamples: int
    bootstrap_rho_bridge: float
    bootstrap_rho_confound: float
    bootstrap_n: int
    source_path: Path | None = None


def load_stage6a_config(path: Path) -> Stage6aConfig:
    with path.open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise ValueError("Stage 6a configuration must be a mapping")
    return Stage6aConfig(
        shapes=tuple(str(value) for value in values.get("shapes", SHAPE_NAMES)),
        rho_bridge_grid=tuple(float(value) for value in values["rho_bridge_grid"]),
        rho_confound_grid=tuple(float(value) for value in values["rho_confound_grid"]),
        sample_sizes=tuple(int(value) for value in values["sample_sizes"]),
        screening_alpha=float(values["screening_alpha"]),
        max_conditioning_size=int(values["max_conditioning_size"]),
        replicates=int(values["replicates"]),
        master_seed=int(values["master_seed"]),
        development_replicates=tuple(int(value) for value in values["development_replicates"]),
        validation_replicates=tuple(int(value) for value in values["validation_replicates"]),
        bootstrap_replicates=int(values["bootstrap_replicates"]),
        bootstrap_resamples=int(values["bootstrap_resamples"]),
        bootstrap_rho_bridge=float(values["bootstrap_rho_bridge"]),
        bootstrap_rho_confound=float(values["bootstrap_rho_confound"]),
        bootstrap_n=int(values["bootstrap_n"]),
        source_path=path.resolve(),
    )


def cells_for(config: Stage6aConfig) -> list[tuple[str, float, float, int]]:
    """Every (shape, rho_bridge, rho_confound, N) cell this config runs --
    shapes that do not depend on the bridge grid (the negative control)
    contribute one nominal rho_bridge value (0.0) instead of repeating
    identical data under every grid value."""
    cells = []
    for shape in config.shapes:
        bridge_grid = config.rho_bridge_grid if USES_BRIDGE_GRID[shape] else (0.0,)
        for rho_bridge in bridge_grid:
            for rho_confound in config.rho_confound_grid:
                for n in config.sample_sizes:
                    cells.append((shape, rho_bridge, rho_confound, n))
    return cells


def _condition_seed(
    master_seed: int, shape_index: int, bridge_index: int, confound_index: int, sample_index: int, replicate: int
) -> int:
    sequence = np.random.SeedSequence(
        [master_seed, _STAGE_TAG, shape_index, bridge_index, confound_index, sample_index, replicate]
    )
    return int(sequence.generate_state(1)[0])


def _pvalue(evidence) -> float:
    return float(evidence.p_value)


def screen_candidate_graph(data: np.ndarray, screening_alpha: float) -> np.ndarray:
    evidence = compute_pairwise_screening_evidence(data)
    return screen_uncorrected(evidence, screening_alpha)


def profile_pair(
    data: np.ndarray, i: int, j: int, pool: list[int], alpha_prune: float, max_conditioning_size: int
) -> tuple[float, float]:
    """(survival fraction, max p-value seen) across conditioning-set sizes
    0..max_conditioning_size drawn from `pool`."""
    per_k_survival = []
    max_p = 0.0
    for k in range(0, max_conditioning_size + 1):
        if len(pool) < k:
            break
        subsets = list(itertools.combinations(pool, k))
        p_values = np.array([_pvalue(compute_partial_correlation_evidence(data, i, j, subset)) for subset in subsets])
        max_p = max(max_p, float(p_values.max()))
        per_k_survival.append(float(np.mean(p_values <= alpha_prune)))
    survival = float(np.mean(per_k_survival)) if per_k_survival else float("nan")
    return survival, max_p


def evaluate_replicate(
    data: np.ndarray, candidates: tuple[tuple[int, int], ...], screening_alpha: float, alpha_prune: float, max_conditioning_size: int
) -> list[dict[str, object]]:
    correlation = np.corrcoef(data, rowvar=False)
    candidate_graph = screen_candidate_graph(data, screening_alpha)
    rows = []
    for i, j in candidates:
        marginal = abs(float(correlation[i, j]))
        if not candidate_graph[i, j]:
            rows.append(dict(pair_i=i, pair_j=j, marg=marginal, surv=0.0, maxp=1.0, screened_out=True))
            continue
        pool = sorted((set(np.flatnonzero(candidate_graph[i])) | set(np.flatnonzero(candidate_graph[j]))) - {i, j})
        survival, max_p = profile_pair(data, i, j, pool, alpha_prune, max_conditioning_size)
        rows.append(dict(pair_i=i, pair_j=j, marg=marginal, surv=survival, maxp=max_p, screened_out=False))
    return rows


def _run_cell(task: tuple[int, str, int, float, int, float, int, int, Stage6aConfig]) -> list[dict[str, object]]:
    """One (shape, rho_bridge, rho_confound, N) cell's full replicate loop,
    self-contained and picklable for a worker process or a CI shard."""
    shape_index, shape_name, bridge_index, rho_bridge, confound_index, rho_confound, sample_index, n, config = task
    shape = make_shape(shape_name, rho_bridge, rho_confound)
    covariance = build_shape_covariance(shape)
    candidates = observed_candidates(shape)
    true_bridges = set(observed_true_bridges(shape))
    alpha_prune = select_form(fit_candidate_forms()).predict(float(n))

    rows: list[dict[str, object]] = []
    for replicate in range(config.replicates):
        seed = _condition_seed(config.master_seed, shape_index, bridge_index, confound_index, sample_index, replicate)
        status, error = "ok", ""
        pair_rows: list[dict[str, object]] = []
        try:
            data = sample_shape(shape, n, np.random.default_rng(seed), covariance=covariance)
            pair_rows = evaluate_replicate(data, candidates, config.screening_alpha, alpha_prune, config.max_conditioning_size)
        except Exception as exc:  # raw evidence must retain sampling/fitting failures
            status, error = "error", f"{type(exc).__name__}: {exc}"

        if not pair_rows:
            pair_rows = [dict(pair_i=i, pair_j=j, marg=np.nan, surv=np.nan, maxp=np.nan, screened_out=None) for i, j in candidates]

        for pair_row in pair_rows:
            rows.append(
                {
                    "shape": shape_name,
                    "rho_bridge": rho_bridge,
                    "rho_confound": rho_confound,
                    "n": n,
                    "alpha_prune": alpha_prune,
                    "replicate": replicate,
                    "seed": seed,
                    "pair": f"{pair_row['pair_i']}-{pair_row['pair_j']}",
                    "is_true_bridge": (pair_row["pair_i"], pair_row["pair_j"]) in true_bridges,
                    "screened_out": pair_row["screened_out"],
                    "marg": pair_row["marg"],
                    "surv": pair_row["surv"],
                    "maxp": pair_row["maxp"],
                    "status": status,
                    "error": error,
                }
            )
    return rows


# --- Generic shard-aggregation contract (see stage5a.py's own comment) -----
load_config = load_stage6a_config
COMBINATION_COLUMNS: tuple[str, ...] = ("shape", "rho_bridge", "rho_confound", "n", "replicate", "pair")


def expected_combinations(config: Stage6aConfig) -> set[tuple[str, float, float, int, int, str]]:
    combos: set[tuple[str, float, float, int, int, str]] = set()
    for shape_name, rho_bridge, rho_confound, n in cells_for(config):
        shape = make_shape(shape_name, rho_bridge, rho_confound)
        candidates = observed_candidates(shape)
        for replicate in range(config.replicates):
            for i, j in candidates:
                combos.add((shape_name, rho_bridge, rho_confound, n, replicate, f"{i}-{j}"))
    return combos


def expected_row_count(config: Stage6aConfig) -> int:
    return len(expected_combinations(config))


def _repository_root(config: Stage6aConfig) -> Path:
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


def _resolved_config(config: Stage6aConfig) -> dict[str, object]:
    return {
        "shapes": list(config.shapes),
        "rho_bridge_grid": list(config.rho_bridge_grid),
        "rho_confound_grid": list(config.rho_confound_grid),
        "sample_sizes": list(config.sample_sizes),
        "screening_alpha": config.screening_alpha,
        "max_conditioning_size": config.max_conditioning_size,
        "replicates": config.replicates,
        "master_seed": config.master_seed,
        "development_replicates": list(config.development_replicates),
        "validation_replicates": list(config.validation_replicates),
        "bootstrap_replicates": config.bootstrap_replicates,
        "bootstrap_resamples": config.bootstrap_resamples,
        "bootstrap_rho_bridge": config.bootstrap_rho_bridge,
        "bootstrap_rho_confound": config.bootstrap_rho_confound,
        "bootstrap_n": config.bootstrap_n,
    }


def _write_evidence(config: Stage6aConfig, output_dir: Path, raw: pd.DataFrame, runtime_seconds: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_resolved_config(config), stream, sort_keys=True)

    repository_root = _repository_root(config)
    charter = repository_root / "docs/stage6a_charter.md"
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


def run_stage6a(
    config: Stage6aConfig,
    output_dir: Path,
    max_workers: int | None = None,
    shapes: tuple[str, ...] | None = None,
    sample_sizes: tuple[int, ...] | None = None,
    write_report: bool = True,
) -> pd.DataFrame:
    """Run every Stage 6a cell. Parallelized and shardable across (shape,
    N) cells -- shape_index/bridge_index/confound_index/sample_index are
    always derived from the full configured grids, so a shard's seeds
    match an unsharded run's."""
    import os
    from concurrent.futures import ProcessPoolExecutor

    run_started = time.perf_counter()
    target_shapes = set(shapes) if shapes is not None else set(config.shapes)
    target_sizes = set(sample_sizes) if sample_sizes is not None else set(config.sample_sizes)

    tasks = []
    for shape_index, shape_name in enumerate(config.shapes):
        if shape_name not in target_shapes:
            continue
        bridge_grid = config.rho_bridge_grid if USES_BRIDGE_GRID[shape_name] else (0.0,)
        for bridge_index, rho_bridge in enumerate(bridge_grid):
            for confound_index, rho_confound in enumerate(config.rho_confound_grid):
                for sample_index, n in enumerate(config.sample_sizes):
                    if n not in target_sizes:
                        continue
                    tasks.append((shape_index, shape_name, bridge_index, rho_bridge, confound_index, rho_confound, sample_index, n, config))
    if not tasks:
        raise ValueError("shapes/sample_sizes filter selected no cells")

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
    _write_evidence(config, output_dir, raw, time.perf_counter() - run_started)
    if not write_report:
        return raw
    from gopcnet.experiments.stage6a_reporting import write_stage6a_report

    write_stage6a_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--shapes", type=str, default=None, help="comma-separated subset of shapes to run")
    parser.add_argument("--sample-sizes", type=str, default=None, help="comma-separated subset of N values to run")
    parser.add_argument("--no-report", action="store_true", help="skip the report (use for CI shards)")
    arguments = parser.parse_args()
    shapes = tuple(arguments.shapes.split(",")) if arguments.shapes else None
    sample_sizes = tuple(int(value) for value in arguments.sample_sizes.split(",")) if arguments.sample_sizes else None
    run_stage6a(
        load_stage6a_config(arguments.config),
        arguments.output,
        arguments.workers,
        shapes=shapes,
        sample_sizes=sample_sizes,
        write_report=not arguments.no_report,
    )


if __name__ == "__main__":
    main()
