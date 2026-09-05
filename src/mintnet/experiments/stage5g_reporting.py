"""Evidence rendering and the predeclared gate for the Stage 5g
growing-subset-DPI comparison. See docs/stage5g_charter.md.

D-047's own GOPC-original ("mint") and D-051's own PC rows are loaded
directly from `evidence/stage5_benchmarks/` (committed, permanent
archives -- see that directory's own README for provenance) rather than
hardcoded, so this report can never silently drift from the archived
numbers via a transcription error.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from mintnet.experiments.stage5a import DGPS
from mintnet.experiments.stage5g import Stage5gConfig, _repository_root

_RECALL_REGRESSION_TOLERANCE = 0.02
_MATERIAL_CLOSURE = 0.5


def _partition(raw: pd.DataFrame, bounds: tuple[int, int]) -> pd.DataFrame:
    return raw.loc[raw["replicate"].between(*bounds)]


def _load_reference(
    repository_root: Path, relative_path: str, method: str, config: Stage5gConfig
) -> dict[tuple[str, int], dict[str, float]]:
    raw = pd.read_csv(repository_root / relative_path)
    raw = raw.loc[raw["method"] == method]
    validation = _partition(raw, config.validation_replicates)
    ok = validation.loc[validation["status"] == "ok"]

    reference: dict[tuple[str, int], dict[str, float]] = {}
    for (dgp, n), group in ok.groupby(["dgp", "n"]):
        reference[(dgp, int(n))] = {
            "precision": float(group["precision"].mean()),
            "recall": float(group["recall"].mean()),
            "f1": float(group["f1"].mean()),
        }
    return reference


@dataclass(frozen=True)
class CellComparison:
    dgp: str
    n: int
    gs_precision: float | None
    gs_recall: float | None
    gs_f1: float | None
    original_precision: float
    original_recall: float
    original_f1: float
    pc_precision: float
    pc_recall: float
    pc_f1: float
    recall_regression: float | None
    recall_ok: bool | None
    gap_present: bool
    closure: float | None


@dataclass(frozen=True)
class ShapeVerdict:
    dgp: str
    n_material: int
    n_partial: int
    n_none: int
    n_gap_cells: int
    verdict: str


@dataclass(frozen=True)
class Stage5gReport:
    by_cell: tuple[CellComparison, ...]
    by_shape: tuple[ShapeVerdict, ...]
    recall_holds: bool
    recall_note: str
    overall_verdict: str


def _cell_comparison(
    raw: pd.DataFrame,
    dgp: str,
    n: int,
    config: Stage5gConfig,
    original_ref: dict[tuple[str, int], dict[str, float]],
    pc_ref: dict[tuple[str, int], dict[str, float]],
) -> CellComparison:
    cell_raw = raw.loc[(raw["dgp"] == dgp) & (raw["n"] == n) & (raw["method"] == "gopc_growing_subset")]
    validation = _partition(cell_raw, config.validation_replicates)
    ok = validation.loc[validation["status"] == "ok"]

    original = original_ref[(dgp, n)]
    pc = pc_ref[(dgp, n)]

    gs_precision = float(ok["precision"].mean()) if not ok.empty else None
    gs_recall = float(ok["recall"].mean()) if not ok.empty else None
    gs_f1 = float(ok["f1"].mean()) if not ok.empty else None

    recall_regression = (original["recall"] - gs_recall) if gs_recall is not None else None
    recall_ok = (recall_regression <= _RECALL_REGRESSION_TOLERANCE) if recall_regression is not None else None

    gap_present = pc["precision"] > original["precision"]
    closure = None
    if gap_present and gs_precision is not None:
        closure = (gs_precision - original["precision"]) / (pc["precision"] - original["precision"])

    return CellComparison(
        dgp, n, gs_precision, gs_recall, gs_f1,
        original["precision"], original["recall"], original["f1"],
        pc["precision"], pc["recall"], pc["f1"],
        recall_regression, recall_ok, gap_present, closure,
    )


def _shape_verdict(dgp: str, cells: tuple[CellComparison, ...]) -> ShapeVerdict:
    shape_cells = [c for c in cells if c.dgp == dgp]
    gap_cells = [c for c in shape_cells if c.gap_present and c.closure is not None]
    n_material = sum(1 for c in gap_cells if c.closure >= _MATERIAL_CLOSURE)
    n_partial = sum(1 for c in gap_cells if 0 < c.closure < _MATERIAL_CLOSURE)
    n_none = sum(1 for c in gap_cells if c.closure <= 0)

    if not gap_cells:
        verdict = "no precision gap present at this shape (nothing to close)"
    elif n_material > len(gap_cells) / 2:
        verdict = f"MATERIAL closure at a majority of gap cells ({n_material}/{len(gap_cells)})"
    elif n_partial + n_material > len(gap_cells) / 2:
        verdict = f"PARTIAL closure at a majority of gap cells ({n_partial}/{len(gap_cells)} partial, {n_material}/{len(gap_cells)} material)"
    else:
        verdict = f"NO closure at a majority of gap cells ({n_none}/{len(gap_cells)})"

    return ShapeVerdict(dgp, n_material, n_partial, n_none, len(gap_cells), verdict)


def _recall_check(cells: tuple[CellComparison, ...]) -> tuple[bool, str]:
    offenders = [c for c in cells if c.recall_ok is False]
    if not offenders:
        return True, (
            f"Recall holds within {_RECALL_REGRESSION_TOLERANCE} of GOPC-original at every tested cell -- "
            "the growing-subset fix does not trade recall for precision."
        )
    worst = max(offenders, key=lambda c: c.recall_regression or 0.0)
    return False, (
        f"Recall regresses by more than {_RECALL_REGRESSION_TOLERANCE} in {len(offenders)} cell(s), worst: "
        f"{worst.dgp} N={worst.n} (original={worst.original_recall:.4f}, "
        f"growing_subset={worst.gs_recall:.4f}) -- REASSESS per the charter's own primary gate, "
        "regardless of any precision gain."
    )


def evaluate_stage5g(raw: pd.DataFrame, config: Stage5gConfig) -> Stage5gReport:
    repository_root = _repository_root(config)
    original_ref = _load_reference(
        repository_root, "evidence/stage5_benchmarks/stage5a_comparator_benchmark/raw_metrics.csv", "mint", config
    )
    pc_ref = _load_reference(
        repository_root, "evidence/stage5_benchmarks/stage5e_pc_skeleton/raw_metrics.csv", "pc", config
    )

    by_cell = tuple(
        _cell_comparison(raw, dgp, n, config, original_ref, pc_ref) for dgp in DGPS for n in config.sample_sizes
    )
    by_shape = tuple(_shape_verdict(dgp, by_cell) for dgp in DGPS)
    recall_holds, recall_note = _recall_check(by_cell)

    diagnosed_shapes = {"chain_fork_hub", "overlap"}
    diagnosed_verdicts = {v.dgp: v for v in by_shape if v.dgp in diagnosed_shapes}
    closes_at_least_partially = all(
        v.n_material > 0 or v.n_partial > 0 or v.n_gap_cells == 0 for v in diagnosed_verdicts.values()
    )

    if not recall_holds:
        overall = "REASSESS -- recall regression at one or more cells (primary gate)."
    elif closes_at_least_partially:
        overall = "PROCEED -- recall holds and at least PARTIAL closure observed on both diagnosed shapes."
    else:
        overall = (
            "REASSESS (on the closure question, not a validity failure) -- recall holds, but the diagnosed "
            "passthrough-scope mechanism does not close the gap on chain_fork_hub and/or overlap; motivates "
            "the hybrid GOPC/PC idea in docs/future_directions.md instead."
        )

    return Stage5gReport(by_cell, by_shape, recall_holds, recall_note, overall)


def write_stage5g_report(raw: pd.DataFrame, config: Stage5gConfig, output_dir: Path) -> Stage5gReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate_stage5g(raw, config)
    (output_dir / "report.json").write_text(
        json.dumps(
            {
                "overall_verdict": report.overall_verdict,
                "recall_holds": report.recall_holds,
                "recall_note": report.recall_note,
                "by_shape": [asdict(s) for s in report.by_shape],
                "by_cell": [asdict(c) for c in report.by_cell],
            },
            indent=2,
            allow_nan=True,
        )
        + "\n",
        encoding="utf-8",
    )

    def fmt(value: float | None) -> str:
        return "None" if value is None else f"{value:.4f}"

    sections = [
        "# Stage 5g Growing-Subset DPI vs. PC Skeleton Report\n",
        f"**Overall: {report.overall_verdict}**\n",
        f"**Recall check: {report.recall_note}**\n",
        "GOPC-original (D-047) and PC (D-051) numbers loaded from "
        "`evidence/stage5_benchmarks/` -- not re-run, computed on identically-seeded data.\n",
        "## Per-shape closure verdict\n",
        "| DGP shape | material | partial | none | gap cells (of 7) | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for s in report.by_shape:
        sections.append(f"| {s.dgp} | {s.n_material} | {s.n_partial} | {s.n_none} | {s.n_gap_cells} | {s.verdict} |")
    sections.append("")

    for dgp in DGPS:
        rows = [
            f"## {dgp}\n",
            "| N | GOPC-original precision | PC precision | growing-subset precision | closure | "
            "original recall | growing-subset recall | recall OK |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in sorted((c for c in report.by_cell if c.dgp == dgp), key=lambda c: c.n):
            rows.append(
                f"| {c.n} | {fmt(c.original_precision)} | {fmt(c.pc_precision)} | {fmt(c.gs_precision)} | "
                f"{fmt(c.closure)} | {fmt(c.original_recall)} | {fmt(c.gs_recall)} | {c.recall_ok} |"
            )
        sections.append("\n".join(rows) + "\n")

    sections.append(
        "Closure = (growing_subset_precision - original_precision) / (pc_precision - original_precision), "
        "computed only where PC's precision exceeds GOPC-original's (a real diagnosed gap). "
        "See `docs/stage5g_charter.md`'s own selection-and-gate section for the frozen criteria.\n"
    )
    (output_dir / "stage5g_report.md").write_text("\n".join(sections), encoding="utf-8")
    return report


write_report = write_stage5g_report
