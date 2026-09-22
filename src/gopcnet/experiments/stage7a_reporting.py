"""Report for Stage 7a (docs/stage7a_charter.md).

Computes gates G1 and G2, Q1 non-inferiority (paired bootstrap CIs on
validation replicates), Q2 engine agreement against a noise floor, and
Q3 runtime. Writes `stage7a_report.md`, `report.json`, and two figures.
Every threshold is the charter's; none is chosen after seeing results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gopcnet.experiments.stage5i import decode_edges
from gopcnet.experiments.stage7a import Stage7aConfig, self_check

G1_ROW_FRACTION = 0.999
NON_INFERIORITY_MARGIN = -0.02  # Stage 5g's recall-regression tolerance (D-053)
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 701


def _validation(raw: pd.DataFrame, config: Stage7aConfig) -> pd.DataFrame:
    low, high = config.validation_replicates
    return raw[(raw["replicate"] >= low) & (raw["replicate"] <= high)]


def _paired(frame: pd.DataFrame, metric: str, a: str, b: str) -> pd.Series:
    wide = frame.pivot_table(index="replicate", columns="method", values=metric, aggfunc="first")
    return (wide[a] - wide[b]).dropna()


def _bootstrap_ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    if len(values) == 0:
        return float("nan"), float("nan")
    draws = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[draws].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def gate_g1(raw: pd.DataFrame) -> dict[str, Any]:
    part_a = raw[(raw["part"] == "A") & raw["method"].isin(["pc_frozen", "pc_core"])]
    wide = part_a.pivot_table(
        index=["name", "level", "replicate"], columns="method", values="edge_bits", aggfunc="first"
    ).dropna()
    if wide.empty:
        return {"passed": None, "rows_compared": 0, "identical_fraction": None}
    identical = float((wide["pc_frozen"] == wide["pc_core"]).mean())
    return {"passed": identical >= G1_ROW_FRACTION, "rows_compared": int(len(wide)), "identical_fraction": identical}


def question_1(raw: pd.DataFrame, config: Stage7aConfig) -> dict[str, Any]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    validation = _validation(raw[(raw["part"] == "A") & (raw["status"] == "ok")], config)
    cells: list[dict[str, Any]] = []
    for (name, level), frame in validation.groupby(["name", "level"]):
        cell: dict[str, Any] = {"shape": name, "n": int(level)}
        passes = True
        for metric in ("precision", "recall"):
            diff = _paired(frame, metric, "gopc_adjacency", "gopc_component")
            low, high = _bootstrap_ci(diff.to_numpy(), rng)
            cell[f"{metric}_diff"] = float(diff.mean()) if len(diff) else float("nan")
            cell[f"{metric}_ci"] = [low, high]
            cell[f"{metric}_pairs"] = int(len(diff))
            passes = passes and (not np.isnan(low)) and low >= NON_INFERIORITY_MARGIN
        cell["non_inferior"] = bool(passes)
        cells.append(cell)
    verdicts = {}
    for shape in sorted({c["shape"] for c in cells}):
        passing = sum(c["non_inferior"] for c in cells if c["shape"] == shape)
        total = sum(1 for c in cells if c["shape"] == shape)
        verdict = "NON-INFERIOR" if passing == total else "MIXED" if passing >= 2 else "INFERIOR"
        verdicts[shape] = {"cells_passing": passing, "cells": total, "verdict": verdict}
    return {"cells": cells, "verdicts": verdicts, "margin": NON_INFERIORITY_MARGIN}


def _symmetric_difference(frame: pd.DataFrame, a: str, b: str, p: int) -> float:
    wide = frame.pivot_table(index="replicate", columns="method", values="edge_bits", aggfunc="first").dropna()
    if wide.empty:
        return float("nan")
    differences = [
        int(np.sum(decode_edges(x, p) != decode_edges(y, p))) for x, y in zip(wide[a], wide[b], strict=True)
    ]
    return float(np.mean(differences))


def question_2(raw: pd.DataFrame, config: Stage7aConfig) -> list[dict[str, Any]]:
    validation = _validation(raw[(raw["part"] == "A") & (raw["status"] == "ok")], config)
    rows = []
    for (name, level), frame in validation.groupby(["name", "level"]):
        p = int(frame["p"].iloc[0])
        rows.append(
            {
                "shape": name,
                "n": int(level),
                "engine_difference": _symmetric_difference(frame, "gopc_adjacency", "gopc_component", p),
                "noise_floor": _symmetric_difference(frame, "gopc_component_floor", "gopc_component", p),
            }
        )
    return rows


def question_3(raw: pd.DataFrame) -> list[dict[str, Any]]:
    part_b = raw[raw["part"] == "B"]
    rows = []
    for (name, level, method), frame in part_b.groupby(["name", "level", "method"]):
        finished = frame[frame["status"] == "ok"]
        rows.append(
            {
                "structure": name,
                "p": int(level),
                "method": method,
                "fits": int(len(frame)),
                "timeouts": int((frame["status"] == "timeout").sum()),
                "errors": int((frame["status"] == "error").sum()),
                "median_seconds": float(finished["elapsed_seconds"].median()) if len(finished) else float("nan"),
                "p90_seconds": float(finished["elapsed_seconds"].quantile(0.9)) if len(finished) else float("nan"),
                "mean_n_tests": float(finished["n_tests_total"].mean()) if len(finished) else float("nan"),
                "mean_f1": float(finished["f1"].mean()) if len(finished) else float("nan"),
            }
        )
    return rows


def _figures(q1: dict[str, Any], q3: list[dict[str, Any]], output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if q1["cells"]:
        shapes = sorted({c["shape"] for c in q1["cells"]})
        fig, axes = plt.subplots(1, 2, figsize=(11, 0.5 + 0.35 * len(q1["cells"])), sharey=True)
        labels = [f'{c["shape"]} N={c["n"]}' for c in q1["cells"]]
        for axis, metric in zip(axes, ("precision", "recall"), strict=True):
            for k, cell in enumerate(q1["cells"]):
                low, high = cell[f"{metric}_ci"]
                colour = "#2b6cb0" if low >= NON_INFERIORITY_MARGIN else "#c53030"
                axis.plot([low, high], [k, k], color=colour)
                axis.plot(cell[f"{metric}_diff"], k, "o", color=colour, markersize=3)
            axis.axvline(0, color="#999", linewidth=0.8)
            axis.axvline(NON_INFERIORITY_MARGIN, color="#c53030", linestyle="--", linewidth=0.8)
            axis.set_title(f"{metric}: adjacency - component")
        axes[0].set_yticks(range(len(labels)), labels, fontsize=7)
        axes[0].invert_yaxis()
        fig.suptitle(f"Stage 7a Q1 non-inferiority ({len(shapes)} shapes, 95% bootstrap CIs)")
        fig.tight_layout()
        fig.savefig(output_dir / "q1_non_inferiority.png", dpi=150)
        plt.close(fig)
    if q3:
        frame = pd.DataFrame(q3)
        fig, axis = plt.subplots(figsize=(7, 4.5))
        for (structure, method), group in frame.groupby(["structure", "method"]):
            group = group.sort_values("p")
            style = "-" if method == "gopc_adjacency" else "--"
            axis.plot(group["p"], group["median_seconds"], style, marker="o", label=f"{method} / {structure}")
        axis.set_yscale("log")
        axis.set_xlabel("p")
        axis.set_ylabel("median seconds per fit (log)")
        axis.set_title("Stage 7a Q3: runtime (timed-out fits excluded; see table)")
        axis.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(output_dir / "q3_runtime_vs_p.png", dpi=150)
        plt.close(fig)


def _fmt(value: float, digits: int = 4) -> str:
    return "n/a" if value is None or (isinstance(value, float) and np.isnan(value)) else f"{value:.{digits}f}"


def write_stage7a_report(raw: pd.DataFrame, config: Stage7aConfig, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    g1 = gate_g1(raw)
    g2 = self_check()
    q1 = question_1(raw, config)
    q2 = question_2(raw, config)
    q3 = question_3(raw)
    status_counts = raw.groupby(["part", "method", "status"]).size().rename("rows").reset_index()
    report = {
        "g1": g1,
        "g2": g2,
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "status_counts": status_counts.to_dict(orient="records"),
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, default=float) + "\n", encoding="utf-8")
    _figures(q1, q3, output_dir)

    lines = [
        "# Stage 7a report: adjacency-set GOPC engine",
        "",
        "Charter: `docs/stage7a_charter.md`. Q1/Q2 use validation replicates only.",
        "",
        "## Gates",
        "",
        f"- **G1** (`pc_core` reproduces `pc_frozen`): {'PASSED' if g1['passed'] else 'FAILED' if g1['passed'] is False else 'not computed'}"
        f" -- identical fraction {_fmt(g1['identical_fraction'])} over {g1['rows_compared']} rows (bar {G1_ROW_FRACTION}).",
        f"- **G2** (correlation primitive equals frozen primitive): {'PASSED' if g2['passed'] else 'FAILED'}"
        f" -- max |difference| {g2['max_abs_difference']:.2e} over {g2['checks']} random checks.",
        "",
        "## Q1 -- non-inferiority (adjacency minus component; margin -0.02 on both metrics)",
        "",
    ]
    for shape, verdict in q1["verdicts"].items():
        lines.append(f"- **{shape}**: {verdict['verdict']} ({verdict['cells_passing']}/{verdict['cells']} cells)")
    lines += ["", "| shape | N | precision diff [95% CI] | recall diff [95% CI] | non-inferior |", "|---|---|---|---|---|"]
    for cell in q1["cells"]:
        lines.append(
            f"| {cell['shape']} | {cell['n']} | {_fmt(cell['precision_diff'])} "
            f"[{_fmt(cell['precision_ci'][0])}, {_fmt(cell['precision_ci'][1])}] | {_fmt(cell['recall_diff'])} "
            f"[{_fmt(cell['recall_ci'][0])}, {_fmt(cell['recall_ci'][1])}] | {cell['non_inferior']} |"
        )
    lines += [
        "",
        "## Q2 -- engine agreement (mean symmetric edge difference per replicate)",
        "",
        "| shape | N | adjacency vs component | noise floor (component at 1.25 x alpha) |",
        "|---|---|---|---|",
    ]
    for row in q2:
        lines.append(f"| {row['shape']} | {row['n']} | {_fmt(row['engine_difference'], 3)} | {_fmt(row['noise_floor'], 3)} |")
    lines += [
        "",
        f"## Q3 -- runtime (N = {config.part_b_n}; component budget {config.component_budget_seconds:g} s per fit)",
        "",
        "| structure | p | method | fits | timeouts | errors | median s | p90 s | mean tests | mean F1 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in q3:
        lines.append(
            f"| {row['structure']} | {row['p']} | {row['method']} | {row['fits']} | {row['timeouts']} | {row['errors']} "
            f"| {_fmt(row['median_seconds'], 2)} | {_fmt(row['p90_seconds'], 2)} | {_fmt(row['mean_n_tests'], 0)} "
            f"| {_fmt(row['mean_f1'], 3)} |"
        )
    lines += ["", "Figures: `q1_non_inferiority.png`, `q3_runtime_vs_p.png`.", ""]
    (output_dir / "stage7a_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


write_report = write_stage7a_report
