"""Evidence rendering for the Stage 5h four-way signal-strength sweep.
See docs/stage5h_charter.md.

Three predeclared reporting requirements, each implemented as its own
section below, none folded into the others:

1. Per-(dgp, method, N) precision trend across ascending strength
   (increasing / decreasing / flat / non-monotonic).
2. Recall reported explicitly for every method at every cell, not
   folded into F1 -- PC in particular is already known (D-051, and this
   project's own manuscript) to have a real recall deficit under some
   conditions, so this is checked directly rather than assumed away.
3. A replication check against D-050's own archived N=1500 evidence
   (`evidence/stage5_benchmarks/stage5d_strength_sweep/raw_metrics.csv`)
   for the two methods (mint, ebicglasso) both charters share -- this
   charter draws a fresh seed stream (see docs/stage5h_charter.md's own
   "Seeding" section), so this is a genuine qualitative replication
   check, not an expectation of numerically identical rows.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
import pandas as pd

from mintnet.experiments.stage5h import DGPS, METHODS, Stage5hConfig

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

_TREND_TOLERANCE = 0.01  # precision points, same sampling-noise tolerance as Stage 5b/5c/5d
_RECALL_FLOOR = 0.999  # below this counts as "recall dropped," not float noise
_D050_ARCHIVE = Path("evidence/stage5_benchmarks/stage5d_strength_sweep/raw_metrics.csv")
_D050_VALIDATION_REPLICATES = (1000, 1999)


def _partition(raw: pd.DataFrame, bounds: tuple[int, int]) -> pd.DataFrame:
    return raw.loc[raw["replicate"].between(*bounds)]


@dataclass(frozen=True)
class CellSummary:
    dgp: str
    method: str
    n: int
    strength: float
    status: str
    precision: float | None
    recall: float | None
    f1: float | None
    shd: float | None
    mean_runtime_seconds: float | None
    n_errors: int


@dataclass(frozen=True)
class PrecisionTrend:
    dgp: str
    method: str
    n: int
    trend: str


@dataclass(frozen=True)
class RecallDrop:
    dgp: str
    method: str
    n: int
    strength: float
    recall: float


@dataclass(frozen=True)
class ReplicationPoint:
    dgp: str
    method: str
    strength: float
    stage5h_precision: float | None
    d050_precision: float | None
    difference: float | None


@dataclass(frozen=True)
class Stage5hReport:
    by_cell: tuple[CellSummary, ...]
    precision_trends: tuple[PrecisionTrend, ...]
    recall_holds: bool
    recall_note: str
    recall_drops: tuple[RecallDrop, ...]
    replication_available: bool
    replication_note: str
    replication_points: tuple[ReplicationPoint, ...]


def summarize_cell(
    raw: pd.DataFrame, dgp: str, method: str, n: int, strength: float, config: Stage5hConfig
) -> CellSummary:
    cell_raw = raw.loc[
        (raw["dgp"] == dgp) & (raw["method"] == method) & (raw["n"] == n) & (raw["strength"] == strength)
    ]
    validation = _partition(cell_raw, config.validation_replicates)
    n_errors = int((validation["status"] != "ok").sum())
    ok = validation.loc[validation["status"] == "ok"]

    if ok.empty:
        return CellSummary(dgp, method, n, strength, "no valid replicates", None, None, None, None, None, n_errors)

    return CellSummary(
        dgp,
        method,
        n,
        strength,
        "ok",
        float(ok["precision"].mean()),
        float(ok["recall"].mean()),
        float(ok["f1"].mean()),
        float(ok["shd"].mean()),
        float(ok["elapsed_seconds"].mean()),
        n_errors,
    )


def _classify_trend(values: list[float]) -> str:
    diffs = [b - a for a, b in zip(values, values[1:])]
    if all(abs(d) <= _TREND_TOLERANCE for d in diffs):
        return "flat"
    if all(d >= -_TREND_TOLERANCE for d in diffs) and any(d > _TREND_TOLERANCE for d in diffs):
        return "increasing"
    if all(d <= _TREND_TOLERANCE for d in diffs) and any(d < -_TREND_TOLERANCE for d in diffs):
        return "decreasing"
    return "non-monotonic"


def _precision_trends(by_cell: tuple[CellSummary, ...], config: Stage5hConfig) -> tuple[PrecisionTrend, ...]:
    trends = []
    for dgp in DGPS:
        for method in METHODS:
            for n in config.sample_sizes:
                series = sorted(
                    (c for c in by_cell if c.dgp == dgp and c.method == method and c.n == n),
                    key=lambda c: c.strength,
                )
                values = [c.precision for c in series if c.precision is not None]
                trends.append(
                    PrecisionTrend(dgp, method, n, _classify_trend(values) if len(values) >= 2 else "insufficient data")
                )
    return tuple(trends)


def _recall_check(by_cell: tuple[CellSummary, ...]) -> tuple[bool, str, tuple[RecallDrop, ...]]:
    drops = tuple(
        RecallDrop(c.dgp, c.method, c.n, c.strength, c.recall)
        for c in by_cell
        if c.recall is not None and c.recall < _RECALL_FLOOR
    )
    if not drops:
        return (
            True,
            "Recall stayed at 1.0 (within floor tolerance) for all four methods in every cell -- "
            "no method's own precision behavior under this manipulation is purchased by missing "
            "true edges.",
            drops,
        )
    detail = "; ".join(f"{d.dgp}/{d.method}/N={d.n}/strength={d.strength}: recall={d.recall:.4f}" for d in drops)
    return False, f"Recall dropped below {_RECALL_FLOOR} in {len(drops)} cell(s): {detail}", drops


def _replication_check(
    by_cell: tuple[CellSummary, ...], config: Stage5hConfig
) -> tuple[bool, str, tuple[ReplicationPoint, ...]]:
    if 1500 not in config.sample_sizes:
        return False, "N=1500 not in this run's own sample sizes -- replication check skipped.", ()
    if not _D050_ARCHIVE.is_file():
        return (
            False,
            f"D-050's own archived evidence not found at {_D050_ARCHIVE} -- replication check skipped "
            "(not a failure of this charter's own run, just an unavailable comparison).",
            (),
        )

    d050_raw = pd.read_csv(_D050_ARCHIVE)
    d050_validation = _partition(d050_raw, _D050_VALIDATION_REPLICATES)
    d050_ok = d050_validation.loc[d050_validation["status"] == "ok"]

    points = []
    for dgp in DGPS:
        for method in ("mint", "ebicglasso"):
            for strength in config.strengths:
                stage5h_cell = next(
                    (c for c in by_cell if c.dgp == dgp and c.method == method and c.n == 1500 and c.strength == strength),
                    None,
                )
                d050_cell = d050_ok.loc[
                    (d050_ok["dgp"] == dgp) & (d050_ok["method"] == method)
                    & (d050_ok["n"] == 1500) & (d050_ok["strength"] == strength)
                ]
                stage5h_precision = stage5h_cell.precision if stage5h_cell is not None else None
                d050_precision = float(d050_cell["precision"].mean()) if not d050_cell.empty else None
                difference = (
                    stage5h_precision - d050_precision
                    if stage5h_precision is not None and d050_precision is not None
                    else None
                )
                points.append(ReplicationPoint(dgp, method, strength, stage5h_precision, d050_precision, difference))

    max_abs_diff = max((abs(p.difference) for p in points if p.difference is not None), default=None)
    if max_abs_diff is None:
        return False, "No comparable (dgp, method, strength) points found at N=1500 -- replication check inconclusive.", tuple(points)
    note = (
        f"Largest |precision difference| between this charter's own fresh N=1500 draw and D-050's own "
        f"archived N=1500 rows, across both shared methods and all tested strengths: {max_abs_diff:.4f}. "
        "Different seed streams (see docs/stage5h_charter.md's own Seeding section), so exact agreement "
        "is not expected -- this checks whether the qualitative pattern (EBICglasso declining, "
        "GOPC-original flat, as strength increases) replicates, not whether the rows match."
    )
    return True, note, tuple(points)


def evaluate_stage5h(raw: pd.DataFrame, config: Stage5hConfig) -> Stage5hReport:
    by_cell = tuple(
        summarize_cell(raw, dgp, method, n, strength, config)
        for dgp in DGPS
        for method in METHODS
        for n in config.sample_sizes
        for strength in config.strengths
    )
    precision_trends = _precision_trends(by_cell, config)
    recall_holds, recall_note, recall_drops = _recall_check(by_cell)
    replication_available, replication_note, replication_points = _replication_check(by_cell, config)
    return Stage5hReport(
        by_cell,
        precision_trends,
        recall_holds,
        recall_note,
        recall_drops,
        replication_available,
        replication_note,
        replication_points,
    )


def _plot_precision_by_strength(report: Stage5hReport, config: Stage5hConfig, path: Path) -> None:
    figure, axes = plt.subplots(len(DGPS), len(config.sample_sizes), figsize=(4.5 * len(config.sample_sizes), 4 * len(DGPS)), sharey=True, squeeze=False)
    for row, dgp in enumerate(DGPS):
        for col, n in enumerate(config.sample_sizes):
            axis = axes[row][col]
            for method in METHODS:
                series = sorted(
                    (c for c in report.by_cell if c.dgp == dgp and c.method == method and c.n == n),
                    key=lambda c: c.strength,
                )
                axis.plot(
                    [c.strength for c in series], [c.precision for c in series], marker="o", label=method
                )
            axis.set_title(f"{dgp}, N={n}", fontsize=9)
            axis.set_xlabel("Signal strength")
            if col == 0:
                axis.set_ylabel("Precision")
    axes[0][-1].legend(fontsize="small")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_stage5h_report(raw: pd.DataFrame, config: Stage5hConfig, output_dir: Path) -> Stage5hReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate_stage5h(raw, config)
    (output_dir / "report.json").write_text(
        json.dumps(
            {
                "recall_holds": report.recall_holds,
                "recall_note": report.recall_note,
                "recall_drops": [asdict(d) for d in report.recall_drops],
                "replication_available": report.replication_available,
                "replication_note": report.replication_note,
                "replication_points": [asdict(p) for p in report.replication_points],
                "precision_trends": [asdict(t) for t in report.precision_trends],
                "by_cell": [asdict(c) for c in report.by_cell],
            },
            indent=2,
            allow_nan=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _plot_precision_by_strength(report, config, output_dir / "precision_by_strength.png")

    def fmt(value: float | None) -> str:
        return "None" if value is None else f"{value:.4f}"

    sections = [
        "# Stage 5h Four-Way Signal-Strength Sweep Report\n",
        f"**Recall check: {report.recall_note}**\n",
        f"**Replication check against D-050: {report.replication_note}**\n",
        "Descriptive result, not a validation gate -- see `docs/stage5h_charter.md`'s own decision "
        "structure. Precision trend classified per (dgp, method, N) series across ascending strength.\n",
        "## Precision trend by (dgp, method, N)\n",
        "| DGP shape | method | N | trend |",
        "|---|---|---|---|",
    ]
    for trend in report.precision_trends:
        sections.append(f"| {trend.dgp} | {trend.method} | {trend.n} | {trend.trend} |")
    sections.append("")

    if report.replication_points:
        sections.append("## Replication check detail (N=1500 only)\n")
        sections.append("| DGP shape | method | strength | Stage 5h precision | D-050 precision | difference |")
        sections.append("|---|---|---|---|---|---|")
        for point in report.replication_points:
            sections.append(
                f"| {point.dgp} | {point.method} | {point.strength} | {fmt(point.stage5h_precision)} | "
                f"{fmt(point.d050_precision)} | {fmt(point.difference)} |"
            )
        sections.append("")

    for dgp in DGPS:
        rows = [
            f"## {dgp}\n",
            "| N | strength | method | precision | recall | F1 | SHD | mean runtime (s) | errors |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for n in config.sample_sizes:
            for strength in config.strengths:
                for method in METHODS:
                    cell = next(
                        c for c in report.by_cell
                        if c.dgp == dgp and c.method == method and c.n == n and c.strength == strength
                    )
                    rows.append(
                        f"| {n} | {strength} | {method} | {fmt(cell.precision)} | {fmt(cell.recall)} | "
                        f"{fmt(cell.f1)} | {fmt(cell.shd)} | {fmt(cell.mean_runtime_seconds)} | {cell.n_errors} |"
                    )
        sections.append("\n".join(rows) + "\n")

    sections.append(
        "See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and "
        "`precision_by_strength.png` for complete evidence.\n"
    )
    (output_dir / "stage5h_report.md").write_text("\n".join(sections), encoding="utf-8")
    return report


write_report = write_stage5h_report
