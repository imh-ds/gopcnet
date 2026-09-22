"""Deterministic raw-evidence runner for Stage 7b: external validity of
GOPC's default against EBICglasso, PC and non-regularized testing on
psych-realistic networks. See docs/stage7b_charter.md.

Per replicate, one true network is drawn per `(structure, p, replicate)`
and reused at every `N` (truth seed independent of `N`), so cells are
paired across sample sizes. Every method is fitted on the same draw, and
the correlation matrix is computed once per draw and shared.

Anchor cells (`legacy_chain_fork_hub`, `p = 15`) use Stage 5a's frozen
sampler and seed derivation, so their draws equal the archived Stage 5g
draws (gate G3).

Sharding: `--structures` x `--ps` x `--sample-sizes`. A shard whose
filters select no cells writes a header-only `raw_metrics.csv`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr

from gopcnet.comparators.ebicglasso import fit_ebicglasso
from gopcnet.comparators.nonregularized import fit_nonregularized_ggm_from_correlation
from gopcnet.comparators.pc_skeleton import fit_pc_skeleton
from gopcnet.defaults import OutsideValidatedRangeWarning, default_dpi_alpha, resolve_alphas
from gopcnet.experiments.stage5a import _DGP_REGISTRY, _condition_seed, _true_adjacency
from gopcnet.experiments.stage5i import encode_edges
from gopcnet.generators.psych_networks import make_truth, sample_data
from gopcnet.pipeline.gopc import fit_gopc
from gopcnet.pipeline.skeleton_core import pc_stable_skeleton
from gopcnet.pipeline.weights import refit_weights_from_correlation
from gopcnet.screening import compute_pairwise_screening_evidence, screen_uncorrected

STAGE_TAG = 702
ANCHOR = "legacy_chain_fork_hub"
ANCHOR_DGP = "chain_fork_hub"
ANCHOR_P = 15
STAGE5A_SAMPLE_SIZES: tuple[int, ...] = (400, 500, 600, 750, 1000, 1500, 1750)
STAGE5A_MASTER_SEED = 20260830
STAGE5A_STRENGTH = 0.5
ANCHOR_METHOD = "gopc_component_anchor"
BRIDGE_P = 10
G1_MAX_P = 20

RAW_COLUMNS: tuple[str, ...] = (
    "structure", "p", "n", "method", "replicate", "seed", "truth_hash", "shrinkage", "true_n_edges",
    "true_mean_abs_weight", "screening_alpha", "dpi_alpha",
    "sensitivity", "specificity", "precision", "f1", "mcc", "shd", "n_estimated_edges",
    "weight_corr_native", "weight_mae_native", "weight_corr_refit", "weight_mae_refit", "strength_spearman",
    "screen_pass_fraction", "null_removed_by_screen", "null_removed_by_prune",
    "true_edges_lost_at_screen", "true_edges_lost_at_prune", "n_tests_total", "cap_reached_count",
    "edge_bits", "elapsed_seconds", "status", "error",
)  # fmt: skip


@dataclass(frozen=True)
class Stage7bConfig:
    structures: tuple[str, ...]
    ps: tuple[int, ...]
    sample_sizes: tuple[int, ...]
    replicates: int
    development_replicates: tuple[int, int]
    validation_replicates: tuple[int, int]
    pc_alphas: tuple[float, ...]
    nonreg_alpha: float
    ebicglasso_gamma: float
    gopc_engine: str
    anchor_sample_sizes: tuple[int, ...]
    g1_subsample_replicates: int
    master_seed: int
    source_path: Path | None = None


def load_stage7b_config(path: Path) -> Stage7bConfig:
    """Load a Stage 7b configuration, retaining the path used to resolve it."""
    with path.open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise ValueError("Stage 7b configuration must be a mapping")
    config = Stage7bConfig(
        structures=tuple(values["structures"]),
        ps=tuple(int(v) for v in values["ps"]),
        sample_sizes=tuple(int(v) for v in values["sample_sizes"]),
        replicates=int(values["replicates"]),
        development_replicates=tuple(int(v) for v in values["development_replicates"]),
        validation_replicates=tuple(int(v) for v in values["validation_replicates"]),
        pc_alphas=tuple(float(v) for v in values["pc_alphas"]),
        nonreg_alpha=float(values["nonreg_alpha"]),
        ebicglasso_gamma=float(values["ebicglasso_gamma"]),
        gopc_engine=str(values["gopc_engine"]),
        anchor_sample_sizes=tuple(int(v) for v in values["anchor_sample_sizes"]),
        g1_subsample_replicates=int(values["g1_subsample_replicates"]),
        master_seed=int(values["master_seed"]),
        source_path=path.resolve(),
    )
    if config.gopc_engine not in ("adjacency", "component"):
        raise ValueError("gopc_engine must be 'adjacency' or 'component'")
    unknown = set(config.anchor_sample_sizes) - set(STAGE5A_SAMPLE_SIZES)
    if unknown:
        raise ValueError(f"anchor sample sizes {sorted(unknown)} are not on Stage 5a's grid")
    return config


# --- cells, methods, and the shard-aggregation contract -----------------


@dataclass(frozen=True)
class Cell:
    structure: str
    structure_index: int
    p: int
    p_index: int
    n: int
    n_index: int


def cells_for(config: Stage7bConfig) -> list[Cell]:
    """All cells, indexed on the full configured grids (never a shard's subset)."""
    cells = [
        Cell(structure, s, p, j, n, k)
        for s, structure in enumerate(config.structures)
        for j, p in enumerate(config.ps)
        for k, n in enumerate(config.sample_sizes)
    ]
    cells += [Cell(ANCHOR, -1, ANCHOR_P, -1, n, STAGE5A_SAMPLE_SIZES.index(n)) for n in config.anchor_sample_sizes]
    return cells


def methods_for(config: Stage7bConfig, cell: Cell) -> tuple[str, ...]:
    if cell.structure == ANCHOR:
        return (ANCHOR_METHOD,)
    methods = ["gopc"]
    if cell.p == BRIDGE_P and config.gopc_engine != "component":
        methods.append("gopc_component")
    methods += [f"pc@{alpha:g}" for alpha in config.pc_alphas]
    if cell.p <= G1_MAX_P:
        methods.append("pc_frozen@0.01")
    methods += ["ebicglasso", "nonreg_holm", "nonreg_bh"]
    return tuple(methods)


def _replicates_for(config: Stage7bConfig, method: str) -> int:
    return min(config.g1_subsample_replicates, config.replicates) if method == "pc_frozen@0.01" else config.replicates


load_config = load_stage7b_config
COMBINATION_COLUMNS: tuple[str, ...] = ("structure", "p", "n", "method")


def expected_row_count(config: Stage7bConfig) -> int:
    return sum(_replicates_for(config, m) for cell in cells_for(config) for m in methods_for(config, cell))


def expected_combinations(config: Stage7bConfig) -> set[tuple[str, int, int, str]]:
    return {(c.structure, c.p, c.n, m) for c in cells_for(config) for m in methods_for(config, c)}


def truth_seed(config: Stage7bConfig, cell: Cell, replicate: int) -> int:
    parts = [config.master_seed, STAGE_TAG, cell.structure_index, cell.p_index, replicate, 0]
    return int(np.random.SeedSequence(parts).generate_state(1)[0])


def data_seed(config: Stage7bConfig, cell: Cell, replicate: int) -> int:
    parts = [config.master_seed, STAGE_TAG, cell.structure_index, cell.p_index, replicate, 1, cell.n_index]
    return int(np.random.SeedSequence(parts).generate_state(1)[0])


# --- scoring -------------------------------------------------------------


def structure_metrics(estimated: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    rows, cols = np.triu_indices(truth.shape[0], k=1)
    est = estimated[rows, cols].astype(bool)
    tru = truth[rows, cols].astype(bool)
    tp = float(np.sum(est & tru))
    fp = float(np.sum(est & ~tru))
    fn = float(np.sum(~est & tru))
    tn = float(np.sum(~est & ~tru))
    sensitivity = tp / (tp + fn) if tp + fn else np.nan
    specificity = tn / (tn + fp) if tn + fp else np.nan
    precision = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else np.nan
    denominator = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else np.nan
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
        "mcc": mcc,
        "shd": fp + fn,
        "n_estimated_edges": tp + fp,
    }


def _upper(matrix: np.ndarray) -> np.ndarray:
    return matrix[np.triu_indices(matrix.shape[0], k=1)]


def weight_metrics(estimated: np.ndarray | None, true_partial: np.ndarray, suffix: str) -> dict[str, float]:
    if estimated is None:
        return {f"weight_corr_{suffix}": np.nan, f"weight_mae_{suffix}": np.nan}
    est, tru = _upper(estimated), _upper(true_partial)
    corr = float(np.corrcoef(est, tru)[0, 1]) if est.std() > 0 and tru.std() > 0 else np.nan
    return {f"weight_corr_{suffix}": corr, f"weight_mae_{suffix}": float(np.mean(np.abs(est - tru)))}


def strength_spearman(estimated: np.ndarray, true_partial: np.ndarray) -> float:
    est = np.abs(estimated).sum(axis=0)
    tru = np.abs(true_partial).sum(axis=0)
    if np.ptp(est) == 0 or np.ptp(tru) == 0:
        return np.nan
    return float(spearmanr(est, tru).statistic)


def mechanism_diagnostics(screened: np.ndarray, adjacency: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    scr, adj, tru = _upper(screened).astype(bool), _upper(adjacency).astype(bool), _upper(truth).astype(bool)
    nulls, trues = max(int((~tru).sum()), 1), max(int(tru.sum()), 1)
    return {
        "screen_pass_fraction": float(scr.mean()),
        "null_removed_by_screen": float((~scr & ~tru).sum() / nulls),
        "null_removed_by_prune": float((scr & ~adj & ~tru).sum() / nulls),
        "true_edges_lost_at_screen": float((~scr & tru).sum() / trues),
        "true_edges_lost_at_prune": float((scr & ~adj & tru).sum() / trues),
    }


# --- fitting -------------------------------------------------------------


def _fit(method: str, data: np.ndarray, corr: np.ndarray, config: Stage7bConfig) -> dict[str, Any]:
    """Returns adjacency, native weights (or None), alphas, and GOPC extras."""
    n, p = data.shape
    out: dict[str, Any] = {"native": None, "screening_alpha": np.nan, "dpi_alpha": np.nan, "extras": {}}
    if method in ("gopc", "gopc_component"):
        engine = config.gopc_engine if method == "gopc" else "component"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OutsideValidatedRangeWarning)
            result = fit_gopc(data, engine=engine)
        out.update(adjacency=result.adjacency, native=result.weights)
        out.update(screening_alpha=result.screening_alpha, dpi_alpha=result.dpi_alpha)
        if method == "gopc":
            if result.diagnostics is not None:
                screened = result.diagnostics.screened
                out["extras"] = {
                    "n_tests_total": float(result.diagnostics.n_tests.sum() / 2),
                    "cap_reached_count": float(np.triu(result.diagnostics.cap_reached, 1).sum()),
                }
            else:
                screened = screen_uncorrected(compute_pairwise_screening_evidence(data), result.screening_alpha)
            out["screened"] = screened
    elif method.startswith("pc@"):
        alpha = float(method.split("@")[1])
        out.update(adjacency=pc_stable_skeleton(corr, n, alpha).adjacency, dpi_alpha=alpha)
    elif method == "pc_frozen@0.01":
        out.update(adjacency=fit_pc_skeleton(data, alpha=0.01).adjacency, dpi_alpha=0.01)
    elif method == "ebicglasso":
        result = fit_ebicglasso(data, gamma=config.ebicglasso_gamma)
        precision = result.precision
        scale = np.sqrt(np.diag(precision))
        partial = -precision / np.outer(scale, scale)
        np.fill_diagonal(partial, 0.0)
        out.update(adjacency=result.adjacency, native=np.where(result.adjacency, partial, 0.0))
    elif method in ("nonreg_holm", "nonreg_bh"):
        correction = "holm" if method == "nonreg_holm" else "bh"
        result = fit_nonregularized_ggm_from_correlation(corr, n, alpha=config.nonreg_alpha, correction=correction)
        out.update(adjacency=result.adjacency, native=result.weights, dpi_alpha=config.nonreg_alpha)
    else:
        raise ValueError(f"unknown method {method}")
    return out


def _empty_row(cell: Cell, method: str, replicate: int, seed: int) -> dict[str, Any]:
    row = {column: np.nan for column in RAW_COLUMNS}
    row.update(
        structure=cell.structure, p=cell.p, n=cell.n, method=method, replicate=replicate, seed=seed,
        truth_hash="", edge_bits="", status="ok", error="",
    )  # fmt: skip
    return row


def _run_psych_cell(cell: Cell, config: Stage7bConfig) -> list[dict[str, Any]]:
    rows = []
    methods = methods_for(config, cell)
    for replicate in range(config.replicates):
        truth = make_truth(cell.structure, cell.p, np.random.default_rng(truth_seed(config, cell, replicate)))
        seed = data_seed(config, cell, replicate)
        data = sample_data(truth, cell.n, np.random.default_rng(seed))
        corr = np.corrcoef(data, rowvar=False)
        true_edges = truth.adjacency
        descriptors = {
            "truth_hash": truth.truth_hash,
            "shrinkage": truth.shrinkage,
            "true_n_edges": float(np.triu(true_edges, 1).sum()),
            "true_mean_abs_weight": float(np.abs(truth.partial_correlations[true_edges]).mean())
            if true_edges.any()
            else np.nan,
        }
        for method in methods:
            if replicate >= _replicates_for(config, method):
                continue
            row = _empty_row(cell, method, replicate, seed)
            row.update(descriptors)
            started = time.perf_counter()
            try:
                fitted = _fit(method, data, corr, config)
                row["elapsed_seconds"] = time.perf_counter() - started
                adjacency = fitted["adjacency"]
                row.update(structure_metrics(adjacency, true_edges))
                row.update(weight_metrics(fitted["native"], truth.partial_correlations, "native"))
                refit = refit_weights_from_correlation(corr, adjacency)
                row.update(weight_metrics(refit, truth.partial_correlations, "refit"))
                row["strength_spearman"] = strength_spearman(refit, truth.partial_correlations)
                row.update(screening_alpha=fitted["screening_alpha"], dpi_alpha=fitted["dpi_alpha"])
                row.update(fitted["extras"])
                if "screened" in fitted:
                    row.update(mechanism_diagnostics(fitted["screened"], adjacency, true_edges))
                row["edge_bits"] = encode_edges(adjacency)
            except Exception as exc:  # raw evidence keeps failures by method
                row.update(status="error", error=f"{type(exc).__name__}: {exc}")
                row["elapsed_seconds"] = time.perf_counter() - started
            rows.append(row)
    return rows


def _run_anchor_cell(cell: Cell, config: Stage7bConfig) -> list[dict[str, Any]]:
    dgp = _DGP_REGISTRY[ANCHOR_DGP]
    truth = _true_adjacency(dgp["true_edges"], int(dgp["p"]))  # type: ignore[arg-type]
    dgp_index = 0  # chain_fork_hub is Stage 5a's first DGP
    dpi_alpha = default_dpi_alpha(cell.n)
    rows = []
    for replicate in range(config.replicates):
        seed = _condition_seed(STAGE5A_MASTER_SEED, dgp_index, cell.n_index, replicate)
        row = _empty_row(cell, ANCHOR_METHOD, replicate, seed)
        started = time.perf_counter()
        try:
            data = dgp["sample"](cell.n, STAGE5A_STRENGTH, np.random.default_rng(seed))  # type: ignore[operator]
            result = fit_gopc(data, screening_alpha=0.001, dpi_alpha=dpi_alpha, engine="component")
            row["elapsed_seconds"] = time.perf_counter() - started
            row.update(structure_metrics(result.adjacency, truth))
            row.update(screening_alpha=0.001, dpi_alpha=dpi_alpha, edge_bits=encode_edges(result.adjacency))
        except Exception as exc:
            row.update(status="error", error=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    return rows


def _run_cell(task: tuple[Cell, Stage7bConfig]) -> list[dict[str, Any]]:
    cell, config = task
    return _run_anchor_cell(cell, config) if cell.structure == ANCHOR else _run_psych_cell(cell, config)


# --- evidence ------------------------------------------------------------


def _repository_root(config: Stage7bConfig) -> Path:
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


def _resolved_config(config: Stage7bConfig) -> dict[str, Any]:
    values = {k: (list(v) if isinstance(v, tuple) else v) for k, v in config.__dict__.items() if k != "source_path"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OutsideValidatedRangeWarning)
        values["default_alphas"] = {
            f"p={p},N={n}": {"screening": a.screening_alpha, "dpi": a.dpi_alpha}
            for p in config.ps
            for n in config.sample_sizes
            for a in [resolve_alphas(n, p)]
        }
    values.update(stage_tag=STAGE_TAG, anchor=ANCHOR, anchor_method=ANCHOR_METHOD)
    return values


def _write_evidence(
    config: Stage7bConfig, output_dir: Path, raw: pd.DataFrame, runtime_seconds: float, git_commit: str | None
) -> None:
    """`git_commit` is HEAD when the run *started* (see D-069's provenance note)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_resolved_config(config), stream, sort_keys=True)
    repository_root = _repository_root(config)
    charter = repository_root / "docs/stage7b_charter.md"
    metadata = {
        "charter_sha256": hashlib.sha256(charter.read_bytes()).hexdigest() if charter.is_file() else None,
        "git_commit": git_commit,
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "runtime_seconds": runtime_seconds,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def run_stage7b(
    config: Stage7bConfig,
    output_dir: Path,
    max_workers: int | None = None,
    structures: tuple[str, ...] | None = None,
    ps: tuple[int, ...] | None = None,
    sample_sizes: tuple[int, ...] | None = None,
    write_report: bool = True,
) -> pd.DataFrame:
    """Run every selected cell; seeds derive from the full grids."""
    started = time.perf_counter()
    git_commit = _git_commit(_repository_root(config))  # recorded at start, not at write time
    tasks = [
        (cell, config)
        for cell in cells_for(config)
        if (structures is None or cell.structure in structures)
        and (ps is None or cell.p in ps)
        and (sample_sizes is None or cell.n in sample_sizes)
    ]
    if max_workers is None:
        max_workers = max(1, (os.cpu_count() or 2) - 1)
    rows: list[dict[str, Any]] = []
    if max_workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=min(max_workers, len(tasks))) as executor:
            for cell_rows in executor.map(_run_cell, tasks):
                rows.extend(cell_rows)
    else:
        for task in tasks:
            rows.extend(_run_cell(task))
    raw = pd.DataFrame(rows, columns=list(RAW_COLUMNS))
    _write_evidence(config, output_dir, raw, time.perf_counter() - started, git_commit)
    if write_report and not raw.empty:
        from gopcnet.experiments.stage7b_reporting import write_stage7b_report

        write_stage7b_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--structures", type=str, default=None)
    parser.add_argument("--ps", type=str, default=None)
    parser.add_argument("--sample-sizes", type=str, default=None)
    parser.add_argument("--no-report", action="store_true", help="skip the report (use for CI shards)")
    arguments = parser.parse_args()
    run_stage7b(
        load_stage7b_config(arguments.config),
        arguments.output,
        arguments.workers,
        structures=tuple(arguments.structures.split(",")) if arguments.structures else None,
        ps=tuple(int(v) for v in arguments.ps.split(",")) if arguments.ps else None,
        sample_sizes=tuple(int(v) for v in arguments.sample_sizes.split(",")) if arguments.sample_sizes else None,
        write_report=not arguments.no_report,
    )


if __name__ == "__main__":
    main()
