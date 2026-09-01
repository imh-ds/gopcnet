"""Deterministic raw-evidence runner for the frozen Stage 5a comparator
benchmark. See docs/stage5a_charter.md.

Runs MINT's conservative engine (`mintnet.pipeline.
compose_screen_then_prune`) and a from-specification EBICglasso
re-implementation (`mintnet.comparators.ebicglasso.fit_ebicglasso`) on
identical simulated data every replicate, on five Gaussian DGP shapes
already validated across Stages 1-4: the composed, noisy chain/fork/hub
p=15 network (`mintnet.experiments.stage4l`), the composed, noisy
shared-node overlap p=15 network (`mintnet.experiments.stage2d`), and
the three-node balanced/moderate/strong triangle fixtures
(`mintnet.simulation.motifs`). No new DGP, no new MINT engine code, no
fresh truth-informed tuning of either method inside this charter.

Implementation-time scope note, made transparently before any evidence
exists: the charter's own text anticipated using overlap's own
specialized `alpha(N)` formula (Stage 4g/4i/4j) inside its validated
`[400, 735]` range. That formula is not a closed-form constant -- it is
a fitted curve object whose fitting inputs (Stage 4e's and Stage 4j's
own archived per-replicate evidence) are not present in this worktree
(`results/generated/` is not committed). Reproducing it here would
require re-running the Stage 4g/4i/4j fitting simulations from scratch,
which is out of scope for a comparator benchmark. This runner instead
uses D-012's general `alpha(N)` formula uniformly across all five
shapes, exactly mirroring `docs/stage4p_charter.md`'s own precedent and
stated rationale ("deliberately, for a fair, consistent comparison") --
not a new decision invented for this charter.
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

from mintnet.comparators.ebicglasso import fit_ebicglasso
from mintnet.experiments import stage2d, stage4l
from mintnet.experiments.stage1j_fit import fit_candidate_forms, select_form
from mintnet.pipeline import compose_screen_then_prune
from mintnet.screening import compute_pairwise_screening_evidence, screen_uncorrected
from mintnet.simulation.motifs import sample_precision_triangle

METHODS: tuple[str, ...] = ("mint", "ebicglasso")
DGPS: tuple[str, ...] = (
    "chain_fork_hub",
    "overlap",
    "triangle_balanced",
    "triangle_moderate",
    "triangle_strong",
)

_STAGE_TAG = 501  # disjoint from every prior charter's own seed derivation


def _triangle_sampler(name: str) -> Callable[[int, float, np.random.Generator], np.ndarray]:
    def sample(n: int, _strength: float, rng: np.random.Generator) -> np.ndarray:
        return sample_precision_triangle(name, n, rng)

    return sample


_TRIANGLE_TRUE_EDGES: frozenset[tuple[int, int]] = frozenset({(0, 1), (0, 2), (1, 2)})

_DGP_REGISTRY: dict[str, dict[str, object]] = {
    "chain_fork_hub": {
        "sample": stage4l._sample_network,
        "p": stage4l.P,
        "true_edges": stage4l.TRUE_DIRECT_EDGES,
    },
    "overlap": {
        "sample": stage2d._sample_network,
        "p": stage2d.P,
        "true_edges": stage2d.TRUE_DIRECT_EDGES,
    },
    "triangle_balanced": {
        "sample": _triangle_sampler("balanced"),
        "p": 3,
        "true_edges": _TRIANGLE_TRUE_EDGES,
    },
    "triangle_moderate": {
        "sample": _triangle_sampler("moderate"),
        "p": 3,
        "true_edges": _TRIANGLE_TRUE_EDGES,
    },
    "triangle_strong": {
        "sample": _triangle_sampler("strong"),
        "p": 3,
        "true_edges": _TRIANGLE_TRUE_EDGES,
    },
}


@dataclass(frozen=True)
class Stage5aConfig:
    sample_sizes: tuple[int, ...]
    strength: float
    screening_alpha: float
    ebicglasso_gamma: float
    ebicglasso_n_lambda: int
    ebicglasso_lambda_min_ratio: float
    replicates: int
    master_seed: int
    development_replicates: tuple[int, int]
    validation_replicates: tuple[int, int]
    source_path: Path | None = None


def _values(values: dict[str, object], key: str, cast: type[int] | type[float]) -> tuple:
    return tuple(cast(value) for value in values[key])


def load_stage5a_config(path: Path) -> Stage5aConfig:
    """Load a Stage 5a configuration, retaining the path used to resolve it."""
    with path.open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream)
    if not isinstance(values, dict):
        raise ValueError("Stage 5a configuration must be a mapping")

    return Stage5aConfig(
        sample_sizes=_values(values, "sample_sizes", int),
        strength=float(values["strength"]),
        screening_alpha=float(values["screening_alpha"]),
        ebicglasso_gamma=float(values["ebicglasso_gamma"]),
        ebicglasso_n_lambda=int(values["ebicglasso_n_lambda"]),
        ebicglasso_lambda_min_ratio=float(values["ebicglasso_lambda_min_ratio"]),
        replicates=int(values["replicates"]),
        master_seed=int(values["master_seed"]),
        development_replicates=tuple(int(value) for value in values["development_replicates"]),
        validation_replicates=tuple(int(value) for value in values["validation_replicates"]),
        source_path=path.resolve(),
    )


def _condition_seed(master_seed: int, dgp_index: int, sample_index: int, replicate: int) -> int:
    sequence = np.random.SeedSequence([master_seed, _STAGE_TAG, dgp_index, sample_index, replicate])
    return int(sequence.generate_state(1)[0])


def _repository_root(config: Stage5aConfig) -> Path:
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


def _resolved_config(config: Stage5aConfig, alpha_by_n: dict[int, float]) -> dict[str, object]:
    return {
        "sample_sizes": list(config.sample_sizes),
        "strength": config.strength,
        "screening_alpha": config.screening_alpha,
        "ebicglasso_gamma": config.ebicglasso_gamma,
        "ebicglasso_n_lambda": config.ebicglasso_n_lambda,
        "ebicglasso_lambda_min_ratio": config.ebicglasso_lambda_min_ratio,
        "replicates": config.replicates,
        "master_seed": config.master_seed,
        "development_replicates": list(config.development_replicates),
        "validation_replicates": list(config.validation_replicates),
        "d012_alpha_by_n": alpha_by_n,
        "note": (
            "MINT uses D-012's general alpha(N) formula uniformly across all five shapes "
            "(overlap's own specialized formula is not reproducible in this worktree -- see "
            "this module's own docstring)."
        ),
    }


def _write_evidence(
    config: Stage5aConfig, output_dir: Path, raw: pd.DataFrame, alpha_by_n: dict[int, float], runtime_seconds: float
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "raw_metrics.csv", index=False)
    with (output_dir / "resolved_config.yaml").open("w", encoding="utf-8") as stream:
        yaml.safe_dump(_resolved_config(config, alpha_by_n), stream, sort_keys=True)

    repository_root = _repository_root(config)
    charter = repository_root / "docs/stage5a_charter.md"
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


def _true_adjacency(true_edges: frozenset[tuple[int, int]], p: int) -> np.ndarray:
    adjacency = np.zeros((p, p), dtype=bool)
    for i, j in true_edges:
        adjacency[i, j] = adjacency[j, i] = True
    return adjacency


def _graph_metrics(estimated: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    p = truth.shape[0]
    rows, cols = np.triu_indices(p, k=1)
    estimated_edges = estimated[rows, cols].astype(bool)
    true_edges = truth[rows, cols].astype(bool)

    true_positive = int(np.sum(estimated_edges & true_edges))
    false_positive = int(np.sum(estimated_edges & ~true_edges))
    false_negative = int(np.sum(~estimated_edges & true_edges))

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else float("nan")
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) and precision == precision and recall == recall else float("nan")
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "shd": float(false_positive + false_negative),
        "n_estimated_edges": float(np.sum(estimated_edges)),
    }


def _mint_adjacency(data: np.ndarray, screening_alpha: float, dpi_alpha: float) -> np.ndarray:
    evidence = compute_pairwise_screening_evidence(data)
    screened = screen_uncorrected(evidence, screening_alpha)
    final, _shapes = compose_screen_then_prune(data, screened, dpi_alpha)
    return final


def run_stage5a(config: Stage5aConfig, output_dir: Path) -> pd.DataFrame:
    """Run MINT's conservative engine and EBICglasso on identical
    simulated data every replicate, across all five DGP shapes and the
    full N grid, paired same-draw per (dgp, N, replicate)."""
    run_started = time.perf_counter()

    selected = select_form(fit_candidate_forms())
    alpha_by_n = {n: selected.predict(float(n)) for n in config.sample_sizes}

    rows: list[dict[str, object]] = []
    for dgp_index, dgp_name in enumerate(DGPS):
        dgp = _DGP_REGISTRY[dgp_name]
        sample: Callable = dgp["sample"]  # type: ignore[assignment]
        p = int(dgp["p"])
        truth = _true_adjacency(dgp["true_edges"], p)  # type: ignore[arg-type]

        for sample_index, n in enumerate(config.sample_sizes):
            dpi_alpha = alpha_by_n[n]
            for replicate in range(config.replicates):
                seed = _condition_seed(config.master_seed, dgp_index, sample_index, replicate)
                try:
                    data = sample(n, config.strength, np.random.default_rng(seed))
                    status, error = "ok", ""
                except Exception as exc:  # raw evidence must retain sampling failures
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
                    selected_lambda: float | None = None
                    if data is not None:
                        try:
                            if method == "mint":
                                estimated = _mint_adjacency(data, config.screening_alpha, dpi_alpha)
                            else:
                                result = fit_ebicglasso(
                                    data,
                                    gamma=config.ebicglasso_gamma,
                                    n_lambda=config.ebicglasso_n_lambda,
                                    lambda_min_ratio=config.ebicglasso_lambda_min_ratio,
                                )
                                estimated = result.adjacency
                                selected_lambda = result.selected_lambda
                            metrics = _graph_metrics(estimated, truth)
                        except Exception as exc:  # retain fitting/scoring failures by method
                            row_status = "error"
                            row_error = f"{type(exc).__name__}: {exc}"

                    rows.append(
                        {
                            "dgp": dgp_name,
                            "method": method,
                            "n": n,
                            "alpha": dpi_alpha if method == "mint" else np.nan,
                            "ebicglasso_lambda": selected_lambda if selected_lambda is not None else np.nan,
                            "replicate": replicate,
                            "seed": seed,
                            **metrics,
                            "elapsed_seconds": time.perf_counter() - started,
                            "status": row_status,
                            "error": row_error,
                        }
                    )
    raw = pd.DataFrame(rows)
    _write_evidence(config, output_dir, raw, alpha_by_n, time.perf_counter() - run_started)
    from mintnet.experiments.stage5a_reporting import write_stage5a_report

    write_stage5a_report(raw, config, output_dir)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    run_stage5a(load_stage5a_config(arguments.config), arguments.output)


if __name__ == "__main__":
    main()
