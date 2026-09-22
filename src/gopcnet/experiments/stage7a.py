"""Deterministic raw-evidence runner for Stage 7a: the adjacency-set GOPC
engine's non-inferiority on the legacy shapes (Part A) and runtime
scaling on psych-realistic structures (Part B). See
docs/stage7a_charter.md.

Both engines are fitted on the same draw inside this run, so every
comparison is paired and needs no archive.

- **Part A:** the five Stage 5a DGPs through their frozen samplers, with
  `gopc_component`, `gopc_adjacency`, `pc_frozen` and `pc_core` (the
  last two for gate G1), plus `gopc_component_floor` (the component
  engine at 1.25 x dpi_alpha, the noise floor for Q2).
- **Part B:** `gopcnet.generators.psych_networks` structures at `N = 500`
  with both engines, each fit in a child process under a wall-clock
  budget. A fit that exceeds the budget is recorded as
  `status = "timeout"`, meaning infeasible.

Sharding: `--names` (DGP or structure names) x `--levels` (N for Part A,
p for Part B). A shard whose filters select no cells writes a
header-only `raw_metrics.csv` and exits normally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml

from gopcnet.comparators.pc_skeleton import fit_pc_skeleton
from gopcnet.defaults import OutsideValidatedRangeWarning, default_dpi_alpha, resolve_alphas
from gopcnet.experiments.stage5a import _DGP_REGISTRY, _graph_metrics, _true_adjacency
from gopcnet.experiments.stage5i import encode_edges
from gopcnet.generators.psych_networks import make_truth, sample_data
from gopcnet.pipeline.gopc import fit_gopc
from gopcnet.pipeline.skeleton_core import pc_stable_skeleton

STAGE_TAG = 701
PART_A_METHODS: tuple[str, ...] = (
    "gopc_component",
    "gopc_adjacency",
    "pc_frozen",
    "pc_core",
    "gopc_component_floor",
)
PART_B_METHODS: tuple[str, ...] = ("gopc_component", "gopc_adjacency")
NOISE_FLOOR_MULTIPLIER = 1.25
RAW_COLUMNS: tuple[str, ...] = (
    "part",
    "name",
    "level",
    "p",
    "n",
    "method",
    "replicate",
    "seed",
    "truth_hash",
    "screening_alpha",
    "dpi_alpha",
    "precision",
    "recall",
    "f1",
    "shd",
    "n_estimated_edges",
    "edge_bits",
    "n_tests_total",
    "elapsed_seconds",
    "status",
    "error",
)


@dataclass(frozen=True)
class Stage7aConfig:
    part_a_dgps: tuple[str, ...]
    part_a_sample_sizes: tuple[int, ...]
    part_a_replicates: int
    part_a_strength: float
    part_a_screening_alpha: float
    pc_alpha: float
    max_conditioning_size: int
    development_replicates: tuple[int, int]
    validation_replicates: tuple[int, int]
    part_b_structures: tuple[str, ...]
    part_b_ps: tuple[int, ...]
    part_b_n: int
    part_b_replicates: int
    component_budget_seconds: float
    master_seed: int
    source_path: Path | None = None


def load_stage7a_config(path: Path) -> Stage7aConfig:
    """Load a Stage 7a configuration, retaining the path used to resolve it."""
    with path.open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise ValueError("Stage 7a configuration must be a mapping")
    return Stage7aConfig(
        part_a_dgps=tuple(values["part_a_dgps"]),
        part_a_sample_sizes=tuple(int(v) for v in values["part_a_sample_sizes"]),
        part_a_replicates=int(values["part_a_replicates"]),
        part_a_strength=float(values["part_a_strength"]),
        part_a_screening_alpha=float(values["part_a_screening_alpha"]),
        pc_alpha=float(values["pc_alpha"]),
        max_conditioning_size=int(values["max_conditioning_size"]),
        development_replicates=tuple(int(v) for v in values["development_replicates"]),
        validation_replicates=tuple(int(v) for v in values["validation_replicates"]),
        part_b_structures=tuple(values["part_b_structures"]),
        part_b_ps=tuple(int(v) for v in values["part_b_ps"]),
        part_b_n=int(values["part_b_n"]),
        part_b_replicates=int(values["part_b_replicates"]),
        component_budget_seconds=float(values["component_budget_seconds"]),
        master_seed=int(values["master_seed"]),
        source_path=path.resolve(),
    )


# --- Generic shard-aggregation contract (see stage5a.py's own comment) -
load_config = load_stage7a_config
COMBINATION_COLUMNS: tuple[str, ...] = ("part", "name", "level", "method")


@dataclass(frozen=True)
class Cell:
    part: str
    name: str
    name_index: int
    level: int  # N for Part A, p for Part B
    level_index: int


def cells_for(config: Stage7aConfig) -> list[Cell]:
    """Every cell, with indices taken from the full configured grids (never a
    shard's filtered subset), so a shard's seeds equal an unsharded run's."""
    cells = [
        Cell("A", dgp, i, n, j)
        for i, dgp in enumerate(config.part_a_dgps)
        for j, n in enumerate(config.part_a_sample_sizes)
    ]
    cells += [
        Cell("B", structure, i, p, j)
        for i, structure in enumerate(config.part_b_structures)
        for j, p in enumerate(config.part_b_ps)
    ]
    return cells


def _replicates(config: Stage7aConfig, part: str) -> int:
    return config.part_a_replicates if part == "A" else config.part_b_replicates


def _methods(part: str) -> tuple[str, ...]:
    return PART_A_METHODS if part == "A" else PART_B_METHODS


def expected_row_count(config: Stage7aConfig) -> int:
    return sum(_replicates(config, c.part) * len(_methods(c.part)) for c in cells_for(config))


def expected_combinations(config: Stage7aConfig) -> set[tuple[str, str, int, str]]:
    return {(c.part, c.name, c.level, m) for c in cells_for(config) for m in _methods(c.part)}


# --- seeding -----------------------------------------------------------


def part_a_seed(config: Stage7aConfig, cell: Cell, replicate: int) -> int:
    sequence = np.random.SeedSequence([config.master_seed, STAGE_TAG, cell.name_index, cell.level_index, replicate])
    return int(sequence.generate_state(1)[0])


def part_b_seeds(config: Stage7aConfig, cell: Cell, replicate: int) -> tuple[int, int]:
    base = [config.master_seed, STAGE_TAG, 100 + cell.name_index, cell.level_index, replicate]
    truth = int(np.random.SeedSequence([*base, 0]).generate_state(1)[0])
    data = int(np.random.SeedSequence([*base, 1]).generate_state(1)[0])
    return truth, data


# --- fitting -------------------------------------------------------------


def _empty_metrics() -> dict[str, float]:
    return {"precision": np.nan, "recall": np.nan, "f1": np.nan, "shd": np.nan, "n_estimated_edges": np.nan}


def _fit_gopc_worker(data: np.ndarray, kwargs: dict[str, Any]) -> tuple[np.ndarray, float]:
    """Top-level (picklable) fit used in child processes and in-process."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OutsideValidatedRangeWarning)
        result = fit_gopc(data, **kwargs)
    n_tests = float(result.diagnostics.n_tests.sum() / 2) if result.diagnostics is not None else np.nan
    return result.adjacency, n_tests


def _child(connection, data: np.ndarray, kwargs: dict[str, Any]) -> None:  # pragma: no cover - runs in a subprocess
    connection.send(("ready", None))  # imports done: the parent's budget starts now
    try:
        started = time.perf_counter()
        adjacency, n_tests = _fit_gopc_worker(data, kwargs)
        connection.send(("ok", (adjacency, n_tests, time.perf_counter() - started)))
    except Exception as exc:  # report, don't hang the parent
        connection.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        connection.close()


def run_with_budget(data: np.ndarray, kwargs: dict[str, Any], budget_seconds: float) -> tuple[str, Any, float]:
    """Fit `fit_gopc(data, **kwargs)` in a spawned child process and terminate
    it if the fit itself exceeds `budget_seconds`. Process startup is excluded:
    the budget and the reported time both start when the child signals it has
    finished importing.

    Returns `(status, payload, fit_seconds)`, where `status` is "ok",
    "error" or "timeout", and `payload` is `(adjacency, n_tests)` on
    success or an error message on failure."""
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(child, data, kwargs))
    process.start()
    child.close()
    try:
        if not parent.poll(300):  # generous: child startup only
            return "error", "child process did not start within 300 s", float("nan")
        parent.recv()  # "ready"
        started = time.perf_counter()
        if parent.poll(budget_seconds):
            status, payload = parent.recv()
            process.join(timeout=10)
            if status == "ok":
                adjacency, n_tests, fit_seconds = payload
                return status, (adjacency, n_tests), fit_seconds
            return status, payload, time.perf_counter() - started
        return "timeout", None, time.perf_counter() - started
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
        parent.close()


def _row(cell: Cell, p: int, n: int, method: str, replicate: int, seed: int, **fields: Any) -> dict[str, Any]:
    row = {
        "part": cell.part,
        "name": cell.name,
        "level": cell.level,
        "p": p,
        "n": n,
        "method": method,
        "replicate": replicate,
        "seed": seed,
        "truth_hash": "",
        "screening_alpha": np.nan,
        "dpi_alpha": np.nan,
        **_empty_metrics(),
        "edge_bits": "",
        "n_tests_total": np.nan,
        "elapsed_seconds": np.nan,
        "status": "ok",
        "error": "",
    }
    row.update(fields)
    return row


def _run_part_a_cell(task: tuple[Cell, Stage7aConfig]) -> list[dict[str, Any]]:
    cell, config = task
    dgp = _DGP_REGISTRY[cell.name]
    sample: Callable = dgp["sample"]  # type: ignore[assignment]
    p = int(dgp["p"])
    truth = _true_adjacency(dgp["true_edges"], p)  # type: ignore[arg-type]
    n = cell.level
    dpi_alpha = default_dpi_alpha(n)
    base = {"screening_alpha": config.part_a_screening_alpha, "max_conditioning_size": config.max_conditioning_size}
    fits: dict[str, Callable[[np.ndarray], tuple[np.ndarray, float]]] = {
        "gopc_component": lambda x: _fit_gopc_worker(x, {**base, "dpi_alpha": dpi_alpha}),
        "gopc_adjacency": lambda x: _fit_gopc_worker(x, {**base, "dpi_alpha": dpi_alpha, "engine": "adjacency"}),
        "pc_frozen": lambda x: (fit_pc_skeleton(x, alpha=config.pc_alpha).adjacency, np.nan),
        "pc_core": lambda x: (
            pc_stable_skeleton(np.corrcoef(x, rowvar=False), x.shape[0], config.pc_alpha).adjacency,
            np.nan,
        ),
        "gopc_component_floor": lambda x: _fit_gopc_worker(
            x, {**base, "dpi_alpha": dpi_alpha * NOISE_FLOOR_MULTIPLIER}
        ),
    }
    alphas = {
        "gopc_component": (config.part_a_screening_alpha, dpi_alpha),
        "gopc_adjacency": (config.part_a_screening_alpha, dpi_alpha),
        "pc_frozen": (np.nan, config.pc_alpha),
        "pc_core": (np.nan, config.pc_alpha),
        "gopc_component_floor": (config.part_a_screening_alpha, dpi_alpha * NOISE_FLOOR_MULTIPLIER),
    }

    rows: list[dict[str, Any]] = []
    for replicate in range(config.part_a_replicates):
        seed = part_a_seed(config, cell, replicate)
        try:
            data = sample(n, config.part_a_strength, np.random.default_rng(seed))
            sample_error = ""
        except Exception as exc:  # raw evidence keeps sampling failures
            data, sample_error = None, f"{type(exc).__name__}: {exc}"
        for method in PART_A_METHODS:
            screening_alpha, method_alpha = alphas[method]
            fields: dict[str, Any] = {"screening_alpha": screening_alpha, "dpi_alpha": method_alpha}
            if data is None:
                rows.append(_row(cell, p, n, method, replicate, seed, status="error", error=sample_error, **fields))
                continue
            started = time.perf_counter()
            try:
                adjacency, n_tests = fits[method](data)
                fields.update(_graph_metrics(adjacency, truth))
                fields.update(edge_bits=encode_edges(adjacency), n_tests_total=n_tests)
            except Exception as exc:  # retain fitting failures by method
                fields.update(status="error", error=f"{type(exc).__name__}: {exc}")
            fields["elapsed_seconds"] = time.perf_counter() - started
            rows.append(_row(cell, p, n, method, replicate, seed, **fields))
    return rows


def _run_part_b_replicate(task: tuple[Cell, Stage7aConfig, int]) -> list[dict[str, Any]]:
    cell, config, replicate = task
    p, n = cell.level, config.part_b_n
    truth_seed, data_seed = part_b_seeds(config, cell, replicate)
    truth = make_truth(cell.name, p, np.random.default_rng(truth_seed))
    data = sample_data(truth, n, np.random.default_rng(data_seed))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OutsideValidatedRangeWarning)
        alphas = resolve_alphas(n, p)
    kwargs = {
        "screening_alpha": alphas.screening_alpha,
        "dpi_alpha": alphas.dpi_alpha,
        "max_conditioning_size": config.max_conditioning_size,
    }
    rows = []
    for method in PART_B_METHODS:
        method_kwargs = {**kwargs, **({"engine": "adjacency"} if method == "gopc_adjacency" else {})}
        # The adjacency engine gets a generous 10x budget only as a hang guard; the
        # charter's feasibility budget applies to the component engine.
        budget = config.component_budget_seconds * (1 if method == "gopc_component" else 10)
        status, payload, elapsed = run_with_budget(data, method_kwargs, budget)
        fields: dict[str, Any] = {
            "truth_hash": truth.truth_hash,
            "screening_alpha": alphas.screening_alpha,
            "dpi_alpha": alphas.dpi_alpha,
            "elapsed_seconds": elapsed,
            "status": status,
        }
        if status == "ok":
            adjacency, n_tests = payload
            fields.update(_graph_metrics(adjacency, truth.adjacency))
            fields.update(edge_bits=encode_edges(adjacency), n_tests_total=n_tests)
        elif status == "error":
            fields["error"] = str(payload)
        else:
            fields["error"] = f"exceeded {budget:g} s budget"
        rows.append(_row(cell, p, n, method, replicate, data_seed, **fields))
    return rows


# --- evidence ------------------------------------------------------------


def self_check(seed: int = 7) -> dict[str, Any]:
    """Gate G2's in-run evidence: the correlation-matrix primitive reproduces
    the frozen residual-based primitive on random inputs (the same property
    tests/unit/test_correlation_based.py pins)."""
    from gopcnet.dpi.correlation_based import partial_correlation_test_from_corr
    from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence

    rng = np.random.default_rng(seed)
    worst = 0.0
    checks = 0
    for _ in range(200):
        n, p = int(rng.choice([60, 400, 2000])), 8
        a = rng.normal(size=(p, p)) * (rng.random((p, p)) < 0.4)
        x = rng.standard_normal((n, p)) @ np.linalg.cholesky(a @ a.T + np.eye(p)).T
        i, j = (int(v) for v in rng.choice(p, size=2, replace=False))
        others = [k for k in range(p) if k not in (i, j)]
        subset = sorted(int(v) for v in rng.choice(others, size=int(rng.integers(0, 5)), replace=False))
        frozen = compute_partial_correlation_evidence(x, i, j, subset).partial_correlation
        fast = partial_correlation_test_from_corr(np.corrcoef(x, rowvar=False), n, i, j, subset).partial_correlation
        worst = max(worst, abs(frozen - fast))
        checks += 1
    return {"checks": checks, "max_abs_difference": worst, "passed": worst <= 1e-10}


def _repository_root(config: Stage7aConfig) -> Path:
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


def _resolved_config(config: Stage7aConfig) -> dict[str, Any]:
    values = {k: (list(v) if isinstance(v, tuple) else v) for k, v in config.__dict__.items() if k != "source_path"}
    values.update(
        stage_tag=STAGE_TAG,
        part_a_methods=list(PART_A_METHODS),
        part_b_methods=list(PART_B_METHODS),
        noise_floor_multiplier=NOISE_FLOOR_MULTIPLIER,
    )
    return values


def _write_evidence(config: Stage7aConfig, output_dir: Path, raw: pd.DataFrame, runtime_seconds: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_resolved_config(config), stream, sort_keys=True)
    repository_root = _repository_root(config)
    charter = repository_root / "docs/stage7a_charter.md"
    metadata = {
        "charter_sha256": hashlib.sha256(charter.read_bytes()).hexdigest() if charter.is_file() else None,
        "git_commit": _git_commit(repository_root),
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "runtime_seconds": runtime_seconds,
        "g2_self_check": self_check(),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def run_stage7a(
    config: Stage7aConfig,
    output_dir: Path,
    max_workers: int | None = None,
    names: tuple[str, ...] | None = None,
    levels: tuple[int, ...] | None = None,
    parts: tuple[str, ...] | None = None,
    write_report: bool = True,
) -> pd.DataFrame:
    """Run every selected cell. Seeds derive from the full grids, so any
    sharding reproduces an unsharded run."""
    started = time.perf_counter()
    selected = [
        cell
        for cell in cells_for(config)
        if (parts is None or cell.part in parts)
        and (names is None or cell.name in names)
        and (levels is None or cell.level in levels)
    ]
    if max_workers is None:
        max_workers = max(1, (os.cpu_count() or 2) - 1)

    rows: list[dict[str, Any]] = []
    part_a = [(cell, config) for cell in selected if cell.part == "A"]
    if part_a:
        if max_workers > 1 and len(part_a) > 1:
            with ProcessPoolExecutor(max_workers=min(max_workers, len(part_a))) as executor:
                for cell_rows in executor.map(_run_part_a_cell, part_a):
                    rows.extend(cell_rows)
        else:
            for task in part_a:
                rows.extend(_run_part_a_cell(task))
    part_b = [(cell, config, r) for cell in selected if cell.part == "B" for r in range(config.part_b_replicates)]
    if part_b:
        # Threads only orchestrate: every fit runs in its own child process.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for replicate_rows in executor.map(_run_part_b_replicate, part_b):
                rows.extend(replicate_rows)

    raw = pd.DataFrame(rows, columns=list(RAW_COLUMNS))
    _write_evidence(config, output_dir, raw, time.perf_counter() - started)
    if write_report and not raw.empty:
        from gopcnet.experiments.stage7a_reporting import write_stage7a_report

        write_stage7a_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--parts", type=str, default=None, help="comma-separated subset of A,B")
    parser.add_argument("--names", type=str, default=None, help="comma-separated DGP/structure names")
    parser.add_argument("--levels", type=str, default=None, help="comma-separated N (Part A) / p (Part B) values")
    parser.add_argument("--no-report", action="store_true", help="skip the report (use for CI shards)")
    arguments = parser.parse_args()
    run_stage7a(
        load_stage7a_config(arguments.config),
        arguments.output,
        arguments.workers,
        names=tuple(arguments.names.split(",")) if arguments.names else None,
        levels=tuple(int(v) for v in arguments.levels.split(",")) if arguments.levels else None,
        parts=tuple(arguments.parts.split(",")) if arguments.parts else None,
        write_report=not arguments.no_report,
    )


if __name__ == "__main__":
    main()
