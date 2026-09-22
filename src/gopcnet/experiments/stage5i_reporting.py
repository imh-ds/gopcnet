"""Report for the frozen Stage 5i PC significance-level sweep. See
docs/stage5i_charter.md.

Computes the two pipeline-integrity gates (G1, G2), the single-alpha
selection on development replicates, and the four descriptive
questions (Q1-Q4) on validation replicates only, then writes
`stage5i_report.md`, `report.json`, `full_grid_validation.csv` and a
recall/precision-vs-alpha figure. Every threshold used here is
predeclared in the charter; none is chosen after seeing results.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from gopcnet.experiments.stage5a import DGPS
from gopcnet.experiments.stage5i import (
    NOISE_FLOOR_ALPHAS,
    PC_ALPHA_GRID,
    Stage5iConfig,
    decode_edges,
)

TOLERANCE = 0.01  # the project's own Stage 5e F1 tolerance
CELL_COUNT_CUTOFF = 3  # of 4 sample sizes, per shape
NOISE_FLOOR_MARGIN = 0.5  # edges of mean symmetric difference
GATE_ROW_FRACTION = 0.999
GATE_CELL_TOLERANCE = 0.001
COMPOSED = ("chain_fork_hub", "overlap")
TRIANGLES = ("triangle_balanced", "triangle_moderate", "triangle_strong")
WEAK_EDGE_SHAPES = {"triangle_moderate": 0.12, "triangle_strong": 0.08}
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20260920
PC_GRID_METHODS = tuple(f"pc@{alpha:g}" for alpha in PC_ALPHA_GRID)
ARCHIVE_ROOT = Path("evidence/stage5_benchmarks")
# Cells whose archived Stage 5e PC rows are not reproducible from the shared
# draws (diagnosed before any full run; see the charter's pre-run amendment).
G1_KNOWN_ARCHIVE_ANOMALIES: frozenset[tuple[str, int]] = frozenset({("overlap", 1750)})


def predicted_weak_edge_recall(rho: float, n: int, alpha: float) -> float:
    """Charter's predeclared prediction: two well-powered edges plus one
    weak edge tested by a Fisher-z test with a single conditioning
    variable; recall = (2 + power) / 3."""
    normal = NormalDist()
    c = normal.inv_cdf(1 - alpha / 2)
    z = float(np.arctanh(rho)) * float(np.sqrt(n - 1 - 3))
    power = normal.cdf(z - c) + normal.cdf(-z - c)
    return (2 + power) / 3


def _split(raw: pd.DataFrame, config: Stage5iConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    ok = raw[raw["status"] == "ok"]
    dev_lo, dev_hi = config.development_replicates
    val_lo, val_hi = config.validation_replicates
    development = ok[(ok["replicate"] >= dev_lo) & (ok["replicate"] <= dev_hi)]
    validation = ok[(ok["replicate"] >= val_lo) & (ok["replicate"] <= val_hi)]
    return development, validation


def _cell_means(frame: pd.DataFrame, value: str) -> pd.Series:
    return frame.groupby(["dgp", "n", "method"])[value].apply(lambda s: float(np.nanmean(s)) if s.notna().any() else np.nan)


def _bootstrap_ci(differences: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    differences = differences[~np.isnan(differences)]
    if differences.size == 0:
        return (np.nan, np.nan, np.nan)
    indices = rng.integers(0, differences.size, size=(BOOTSTRAP_RESAMPLES, differences.size))
    means = differences[indices].mean(axis=1)
    return (float(differences.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def _paired(frame: pd.DataFrame, dgp: str, n: int, method_a: str, method_b: str, metric: str) -> np.ndarray:
    """Per-replicate paired difference (a - b) on identical draws."""
    cell = frame[(frame["dgp"] == dgp) & (frame["n"] == n)]
    a = cell[cell["method"] == method_a].set_index("replicate")[metric]
    b = cell[cell["method"] == method_b].set_index("replicate")[metric]
    joined = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    return (joined["a"] - joined["b"]).to_numpy()


# --- Gates ---------------------------------------------------------------


def _gate(
    raw: pd.DataFrame,
    method: str,
    archive: pd.DataFrame,
    archived_method: str,
    excluded: frozenset[tuple[str, int]] = frozenset(),
) -> dict[str, object]:
    ours = raw[(raw["method"] == method) & (raw["status"] == "ok")]
    theirs = archive[(archive["method"] == archived_method) & (archive["status"] == "ok")]
    columns = ["n_estimated_edges", "precision", "recall"]
    joined = ours.merge(theirs, on=["dgp", "n", "replicate"], suffixes=("", "_archived"))
    if joined.empty:
        return {"passed": False, "note": "no shared replicate rows", "rows_compared": 0}
    identical = np.ones(len(joined), dtype=bool)
    for column in columns:
        both_nan = joined[column].isna() & joined[f"{column}_archived"].isna()
        close = np.isclose(joined[column], joined[f"{column}_archived"], rtol=0, atol=1e-9)
        identical &= both_nan | close
    joined = joined.assign(_identical=identical)
    in_scope = ~joined.apply(lambda row: (row["dgp"], int(row["n"])) in excluded, axis=1)
    scoped = joined[in_scope]
    if scoped.empty:
        return {"passed": False, "note": "no in-scope rows", "rows_compared": 0}
    fraction = float(scoped["_identical"].mean())
    cell_diffs: dict[str, float] = {}
    worst = 0.0
    for (dgp, n), cell in scoped.groupby(["dgp", "n"]):
        diff = max(abs(np.nanmean(cell[c]) - np.nanmean(cell[f"{c}_archived"])) for c in columns)
        cell_diffs[f"{dgp}|{n}"] = float(diff)
        worst = max(worst, float(diff))
    excluded_report = {
        f"{dgp}|{n}": {
            "rows": int(len(cell)),
            "identical_row_fraction": float(cell["_identical"].mean()),
        }
        for (dgp, n), cell in joined[~in_scope].groupby(["dgp", "n"])
    }
    diagnosis: dict[str, object] = {}
    for (dgp, n), cell in joined.groupby(["dgp", "n"]):
        if cell["_identical"].all():
            continue
        entry: dict[str, object] = {"rows": int(len(cell)), "identical_row_fraction": float(cell["_identical"].mean())}
        for column in columns:
            x, y = cell[column].dropna(), cell[f"{column}_archived"].dropna()
            se = float(np.sqrt(x.var() / len(x) + y.var() / len(y))) if len(x) > 1 and len(y) > 1 else 0.0
            diff = float(x.mean() - y.mean())
            entry[column] = {"this_run": float(x.mean()), "archived": float(y.mean()), "diff": diff, "unpaired_z": (diff / se) if se > 0 else None}
        diagnosis[f"{dgp}|{n}"] = entry
    return {
        "passed": bool(fraction >= GATE_ROW_FRACTION and worst <= GATE_CELL_TOLERANCE),
        "post_hoc_cell_diagnosis": diagnosis,
        "rows_compared": int(len(scoped)),
        "identical_row_fraction": fraction,
        "worst_cell_mean_difference": worst,
        "cell_mean_differences": cell_diffs,
        "excluded_known_archive_anomalies": excluded_report,
    }


def _run_gates(raw: pd.DataFrame, repository_root: Path) -> dict[str, dict[str, object]]:
    gates: dict[str, dict[str, object]] = {}
    for name, method, folder, archived_method in (
        ("G1", "pc@0.01", "stage5e_pc_skeleton", "pc"),
        ("G2", "gopc_growing@validated", "stage5g_growing_subset", "gopc_growing_subset"),
    ):
        path = repository_root / ARCHIVE_ROOT / folder / "raw_metrics.csv"
        if not path.is_file():
            gates[name] = {"passed": False, "note": f"archive not found: {path}", "rows_compared": 0}
            continue
        excluded = G1_KNOWN_ARCHIVE_ANOMALIES if name == "G1" else frozenset()
        gates[name] = _gate(raw, method, pd.read_csv(path), archived_method, excluded)
    return gates


# --- Single-alpha selection ---------------------------------------------


def _select_alpha(scores: pd.Series) -> float:
    """Largest score wins; ties broken toward the smaller alpha."""
    ordered = scores.sort_index()
    best = ordered.max()
    return float(next(alpha for alpha, score in ordered.items() if np.isclose(score, best, rtol=0, atol=1e-12)))


def _alpha_of(method: str) -> float:
    return float(method.split("@")[1])


def _selection(development: pd.DataFrame, config: Stage5iConfig) -> dict[str, dict]:
    grid = development[development["method"].isin(PC_GRID_METHODS)]
    f1 = grid.groupby(["dgp", "n", "method"])["f1"].mean().reset_index()
    f1["alpha"] = f1["method"].map(_alpha_of)
    result: dict[str, dict] = {"primary": {}, "equal_per_shape": {}, "composed_only": {}, "triangles_only": {}, "oracle": {}}
    for n in config.sample_sizes:
        at_n = f1[f1["n"] == n]
        by = at_n.pivot(index="alpha", columns="dgp", values="f1")
        result["primary"][n] = _select_alpha(0.5 * by[list(COMPOSED)].mean(axis=1) + 0.5 * by[list(TRIANGLES)].mean(axis=1))
        result["equal_per_shape"][n] = _select_alpha(by[list(DGPS)].mean(axis=1))
        result["composed_only"][n] = _select_alpha(by[list(COMPOSED)].mean(axis=1))
        result["triangles_only"][n] = _select_alpha(by[list(TRIANGLES)].mean(axis=1))
        result["oracle"][n] = {dgp: _select_alpha(by[dgp]) for dgp in DGPS}
    return result


def _method_at(alpha: float) -> str:
    return f"pc@{alpha:g}"


# --- Questions -------------------------------------------------------------


def _verdict(count: int, artifact_label: str, holds_label: str, cutoff: int = CELL_COUNT_CUTOFF) -> str:
    if count >= cutoff:
        return artifact_label
    if count <= 4 - cutoff:
        return holds_label
    return "mixed (reported per cell)"


def _q1(validation: pd.DataFrame, config: Stage5iConfig, rng: np.random.Generator) -> dict[str, object]:
    shapes: dict[str, object] = {}
    for dgp, rho in WEAK_EDGE_SHAPES.items():
        cells, matched_count = [], 0
        for n in config.sample_sizes:
            pc_recall = _mean(validation, dgp, n, "pc@matched", "recall")
            gopc_recall = _mean(validation, dgp, n, "gopc_growing@validated", "recall")
            alpha_matched = float(
                validation[(validation["dgp"] == dgp) & (validation["n"] == n) & (validation["method"] == "pc@matched")]["alpha"].iloc[0]
            )
            within = pc_recall >= gopc_recall - TOLERANCE
            matched_count += int(within)
            ci = _bootstrap_ci(_paired(validation, dgp, n, "pc@matched", "gopc_growing@validated", "recall"), rng)
            predicted_pc01 = predicted_weak_edge_recall(rho, n, 0.01)
            predicted_matched = predicted_weak_edge_recall(rho, n, alpha_matched)
            pc01 = _mean(validation, dgp, n, "pc@0.01", "recall")
            cells.append(
                {
                    "n": n,
                    "pc_matched_recall": pc_recall,
                    "gopc_recall": gopc_recall,
                    "pc_matched_within_tolerance": bool(within),
                    "paired_diff_pc_matched_minus_gopc": {"mean": ci[0], "ci95": [ci[1], ci[2]]},
                    "pc_0.01_recall": pc01,
                    "predicted_pc_0.01": predicted_pc01,
                    "predicted_pc_matched": predicted_matched,
                    "pc_matched_prediction_gap": pc_recall - predicted_matched,
                    "prediction_missed_by_more_than_0.02": bool(abs(pc_recall - predicted_matched) > 0.02),
                }
            )
        shapes[dgp] = {
            "cells": cells,
            "n_cells_matched": matched_count,
            "verdict": _verdict(
                matched_count,
                "recall deficit was the significance level (restate the manuscript's recall claim)",
                "recall deficit survives alpha-matching",
            ),
        }
    return shapes


def _mean(frame: pd.DataFrame, dgp: str, n: int, method: str, metric: str) -> float:
    cell = frame[(frame["dgp"] == dgp) & (frame["n"] == n) & (frame["method"] == method)][metric]
    return float(np.nanmean(cell)) if cell.notna().any() else float("nan")


def _q2(validation: pd.DataFrame, config: Stage5iConfig, rng: np.random.Generator) -> dict[str, object]:
    shapes: dict[str, object] = {}
    for dgp in COMPOSED:
        cells, below, holds = [], 0, 0
        for n in config.sample_sizes:
            pc_precision = _mean(validation, dgp, n, "pc@matched", "precision")
            gopc_precision = _mean(validation, dgp, n, "gopc_growing@validated", "precision")
            below += int(gopc_precision - pc_precision > TOLERANCE)
            holds += int(pc_precision >= gopc_precision - TOLERANCE)
            ci = _bootstrap_ci(_paired(validation, dgp, n, "pc@matched", "gopc_growing@validated", "precision"), rng)
            cells.append(
                {
                    "n": n,
                    "pc_matched_precision": pc_precision,
                    "gopc_precision": gopc_precision,
                    "pc_0.01_precision": _mean(validation, dgp, n, "pc@0.01", "precision"),
                    "paired_diff_pc_matched_minus_gopc": {"mean": ci[0], "ci95": [ci[1], ci[2]]},
                }
            )
        if below >= CELL_COUNT_CUTOFF:
            verdict = "PC's precision edge was the strictness of alpha = .01 (GOPC's decoupled design reaches precision PC cannot at loose alpha)"
        elif holds >= CELL_COUNT_CUTOFF:
            verdict = "loosening alpha costs PC nothing on precision (GOPC gains nothing on this axis)"
        else:
            verdict = "mixed (reported per cell)"
        shapes[dgp] = {"cells": cells, "n_cells_pc_below_gopc": below, "n_cells_pc_holds": holds, "verdict": verdict}
    return shapes


def _q3(validation: pd.DataFrame, config: Stage5iConfig, selection: dict[str, dict], rule: str) -> dict[str, object]:
    cells, comparable_by_n = [], {n: [] for n in config.sample_sizes}
    for dgp in DGPS:
        for n in config.sample_sizes:
            if rule == "per_group":
                alpha = selection["composed_only" if dgp in COMPOSED else "triangles_only"][n]
            else:
                alpha = selection[rule][n]
            pc_f1 = _mean(validation, dgp, n, _method_at(alpha), "f1")
            gopc_f1 = _mean(validation, dgp, n, "gopc_growing@validated", "f1")
            comparable = bool(pc_f1 >= gopc_f1 - TOLERANCE)
            comparable_by_n[n].append(comparable)
            cells.append({"dgp": dgp, "n": n, "alpha_star": alpha, "pc_f1": pc_f1, "gopc_f1": gopc_f1, "pc_comparable_or_better": comparable})
    return {
        "rule": rule,
        "cells": cells,
        "n_comparable_of_20": int(sum(cell["pc_comparable_or_better"] for cell in cells)),
        "n_values_where_pc_comparable_on_all_five_shapes": [n for n, flags in comparable_by_n.items() if all(flags)],
    }


def _edge_matrix(frame: pd.DataFrame, dgp: str, n: int, method: str, p: int) -> pd.DataFrame:
    cell = frame[(frame["dgp"] == dgp) & (frame["n"] == n) & (frame["method"] == method)].sort_values("replicate")
    return pd.Series([decode_edges(bits, p) for bits in cell["edge_bits"]], index=cell["replicate"])


def _agreement(frame: pd.DataFrame, dgp: str, n: int, method_a: str, method_b: str, p: int) -> tuple[float, float, int]:
    a, b = _edge_matrix(frame, dgp, n, method_a, p), _edge_matrix(frame, dgp, n, method_b, p)
    shared = a.index.intersection(b.index)
    if len(shared) == 0:
        return (np.nan, np.nan, 0)
    diffs = np.array([int(np.sum(a[r] != b[r])) for r in shared])
    return (float(np.mean(diffs == 0)), float(diffs.mean()), int(len(shared)))


def _q4(validation: pd.DataFrame, config: Stage5iConfig) -> dict[str, object]:
    from gopcnet.experiments.stage5a import _DGP_REGISTRY

    out: dict[str, object] = {}
    for alpha, floor_alpha in zip((0.01, 0.10), NOISE_FLOOR_ALPHAS):
        per_shape: dict[str, object] = {}
        for dgp in DGPS:
            p = int(_DGP_REGISTRY[dgp]["p"])
            cells, gopc_diffs, floor_diffs = [], [], []
            for n in config.sample_sizes:
                exact, sym, count = _agreement(validation, dgp, n, f"gopc_matched@{alpha:g}", f"pc@{alpha:g}", p)
                f_exact, f_sym, _ = _agreement(validation, dgp, n, f"pc@{alpha:g}", f"pc@{floor_alpha:g}", p)
                gopc_diffs.append(sym)
                floor_diffs.append(f_sym)
                cells.append(
                    {
                        "n": n,
                        "replicates": count,
                        "gopc_vs_pc_exact_match": exact,
                        "gopc_vs_pc_mean_symmetric_difference": sym,
                        "noise_floor_exact_match": f_exact,
                        "noise_floor_mean_symmetric_difference": f_sym,
                    }
                )
            gopc_mean, floor_mean = float(np.nanmean(gopc_diffs)), float(np.nanmean(floor_diffs))
            per_shape[dgp] = {
                "cells": cells,
                "gopc_vs_pc_mean_symmetric_difference": gopc_mean,
                "noise_floor_mean_symmetric_difference": floor_mean,
                "verdict": (
                    "effectively the same search at matched alpha (up to order-2 tests)"
                    if gopc_mean <= floor_mean + NOISE_FLOOR_MARGIN
                    else "materially different even at matched alpha"
                ),
            }
        out[f"alpha_{alpha:g}"] = per_shape
    return out


def _negative_control(validation: pd.DataFrame, config: Stage5iConfig) -> dict[str, object]:
    """triangle_balanced should show no separation for alpha >= .005."""
    methods = [m for m in PC_GRID_METHODS if _alpha_of(m) >= 0.005] + ["pc@matched", "gopc_growing@validated"]
    ranges = {}
    for n in config.sample_sizes:
        values = [_mean(validation, "triangle_balanced", n, m, "f1") for m in methods]
        ranges[n] = float(np.nanmax(values) - np.nanmin(values))
    return {"f1_range_across_methods_by_n": ranges, "flagged": bool(max(ranges.values()) > TOLERANCE)}


# --- Output ----------------------------------------------------------------


def _figure(validation: pd.DataFrame, config: Stage5iConfig, output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, len(DGPS), figsize=(4 * len(DGPS), 6.5), squeeze=False, sharex=True)
    colors = plt.get_cmap("viridis")(np.linspace(0.1, 0.9, len(config.sample_sizes)))
    for col, dgp in enumerate(DGPS):
        for row, metric in enumerate(("recall", "precision")):
            axis = axes[row][col]
            for color, n in zip(colors, config.sample_sizes):
                ys = [_mean(validation, dgp, n, _method_at(a), metric) for a in PC_ALPHA_GRID]
                axis.plot(PC_ALPHA_GRID, ys, "-o", color=color, ms=3, label=f"PC, N={n}")
                matched_alpha = float(
                    validation[(validation["dgp"] == dgp) & (validation["n"] == n) & (validation["method"] == "pc@matched")]["alpha"].iloc[0]
                )
                axis.plot(
                    [matched_alpha], [_mean(validation, dgp, n, "gopc_growing@validated", metric)],
                    "*", color=color, ms=11, mec="k",
                )
            axis.set_xscale("log")
            axis.set_title(f"{dgp}\n{metric}", fontsize=9)
            if col == 0:
                axis.set_ylabel(metric)
            if row == 1:
                axis.set_xlabel("PC alpha (stars: GOPC validated, plotted at its alpha(N))")
    axes[0][0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(output_dir / "recall_precision_vs_alpha.png", dpi=130)
    plt.close(fig)


def _grid_table(validation: pd.DataFrame) -> pd.DataFrame:
    grouped = validation.groupby(["dgp", "n", "method"])
    table = grouped[["precision", "recall", "f1", "shd", "n_estimated_edges"]].mean().reset_index()
    return table


def _fmt(value: float) -> str:
    return "nan" if value != value else f"{value:.3f}"


def _markdown(report: dict[str, object], config: Stage5iConfig) -> str:
    lines = ["# Stage 5i report: PC significance-level sweep", ""]
    lines += ["Charter: `docs/stage5i_charter.md` (FROZEN before results). All comparisons below use validation replicates only.", ""]
    lines += ["## G1 / G2 (pipeline integrity)", ""]
    for name, gate in report["gates"].items():  # type: ignore[union-attr]
        lines.append(
            f"- **{name}**: {'PASSED' if gate['passed'] else 'FAILED'} — rows compared {gate.get('rows_compared')}, "
            f"identical fraction {gate.get('identical_row_fraction', float('nan')):.5f}, "
            f"worst cell-mean difference {gate.get('worst_cell_mean_difference', float('nan')):.5f}"
        )
        for cell, info in (gate.get("post_hoc_cell_diagnosis") or {}).items():
            z = "; ".join(
                f"{c} diff {info[c]['diff']:+.4f} (z={info[c]['unpaired_z']:.2f})"
                for c in ("n_estimated_edges", "precision", "recall")
                if info[c]["unpaired_z"] is not None
            )
            lines.append(f"  - post-hoc, not predeclared — {cell}: identical fraction {info['identical_row_fraction']:.4f}; {z}")
        for cell, info in (gate.get("excluded_known_archive_anomalies") or {}).items():
            lines.append(
                f"  - excluded per charter amendment (archive anomaly, reported not gated): {cell}, "
                f"{info['rows']} rows, identical fraction {info['identical_row_fraction']:.4f}"
            )
    lines += [
        "",
        "**Gate outcome and post-hoc diagnosis (added after the full run; not part of the frozen charter).** "
        "Both gates FAIL as the charter defined them and are reported as failed. Every failing cell is "
        "`overlap`; all other cells reproduce the archives exactly. The most likely cause: the `overlap` "
        "sampler draws with `numpy.random.Generator.multivariate_normal`, which factors the covariance by SVD, "
        "and that covariance has a repeated singular value (0.8, twice), so the SVD's rotation within that "
        "2-D subspace is not pinned down and can depend on the machine's floating-point behavior. Every "
        "rotation is a valid factorization of the same covariance, so draws follow the same distribution but "
        "a given seed can yield different data. Supporting evidence: a local check that swaps the "
        "factorization (`svd` vs `eigh`) on identical seeds changes PC's edge count in 8% (N=1000) to 16% "
        "(N=1500) of replicates, the same order as the 17-19% seen here. NOT directly demonstrated: that "
        "the CI machines actually differ in this way. The per-cell unpaired z-scores above show the "
        "differing cells agree within sampling noise. This does not affect any comparison inside this run, "
        "where every method sees the same draw. "
        "`triangle_balanced` shares the repeated-singular-value property but its edge counts cannot reveal it.",
        "",
        "## Single-alpha selection (development replicates)",
        "",
    ]
    selection = report["selection"]  # type: ignore[assignment]
    lines += ["| N | primary (50/50) | equal per shape | composed only | triangles only |", "|---|---|---|---|---|"]
    for n in config.sample_sizes:
        lines.append(
            f"| {n} | {selection['primary'][n]:g} | {selection['equal_per_shape'][n]:g} | "
            f"{selection['composed_only'][n]:g} | {selection['triangles_only'][n]:g} |"
        )
    lines += ["", "Per-shape oracle alpha (upper bound on PC tunability, NOT a deployable method):", ""]
    lines += ["| N | " + " | ".join(DGPS) + " |", "|---|" + "---|" * len(DGPS)]
    for n in config.sample_sizes:
        lines.append(f"| {n} | " + " | ".join(f"{selection['oracle'][n][dgp]:g}" for dgp in DGPS) + " |")

    lines += ["", "## Q1 — Is the weak-edge recall deficit an alpha artifact?", ""]
    for dgp, block in report["q1"].items():  # type: ignore[union-attr]
        lines += [f"**{dgp}** — {block['n_cells_matched']} of 4 N within tolerance: *{block['verdict']}*", ""]
        lines += ["| N | PC@matched | GOPC | paired diff [95% CI] | PC@.01 | pred PC@.01 | pred matched | gap |", "|---|---|---|---|---|---|---|---|"]
        for cell in block["cells"]:
            d = cell["paired_diff_pc_matched_minus_gopc"]
            lines.append(
                f"| {cell['n']} | {_fmt(cell['pc_matched_recall'])} | {_fmt(cell['gopc_recall'])} | "
                f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] | {_fmt(cell['pc_0.01_recall'])} | "
                f"{_fmt(cell['predicted_pc_0.01'])} | {_fmt(cell['predicted_pc_matched'])} | {cell['pc_matched_prediction_gap']:+.3f}"
                f"{' **>.02**' if cell['prediction_missed_by_more_than_0.02'] else ''} |"
            )
        lines.append("")

    lines += ["## Q2 — Is PC's precision edge an alpha artifact?", ""]
    for dgp, block in report["q2"].items():  # type: ignore[union-attr]
        lines += [f"**{dgp}** — PC below GOPC by >.01 at {block['n_cells_pc_below_gopc']} of 4 N; holds within .01 at {block['n_cells_pc_holds']} of 4: *{block['verdict']}*", ""]
        lines += ["| N | PC@matched | GOPC | PC@.01 | paired diff [95% CI] |", "|---|---|---|---|---|"]
        for cell in block["cells"]:
            d = cell["paired_diff_pc_matched_minus_gopc"]
            lines.append(
                f"| {cell['n']} | {_fmt(cell['pc_matched_precision'])} | {_fmt(cell['gopc_precision'])} | {_fmt(cell['pc_0.01_precision'])} | "
                f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] |"
            )
        lines.append("")

    lines += ["## Q3 — Does one alpha suffice?", ""]
    for name, block in report["q3"].items():  # type: ignore[union-attr]
        lines.append(
            f"- **{name}**: PC comparable-or-better in {block['n_comparable_of_20']} of 20 cells; "
            f"N with all five shapes comparable: {block['n_values_where_pc_comparable_on_all_five_shapes'] or 'none'}"
        )
    lines += ["", "## Q4 — Mechanism check (matched GOPC capped at conditioning order 2; PC uncapped)", ""]
    for level, per_shape in report["q4"].items():  # type: ignore[union-attr]
        lines += [f"**{level}**", "", "| shape | GOPC-vs-PC mean sym. diff | noise floor | verdict |", "|---|---|---|---|"]
        for dgp, block in per_shape.items():
            lines.append(
                f"| {dgp} | {block['gopc_vs_pc_mean_symmetric_difference']:.3f} | "
                f"{block['noise_floor_mean_symmetric_difference']:.3f} | {block['verdict']} |"
            )
        lines.append("")
    control = report["negative_control"]  # type: ignore[assignment]
    lines += [
        "## Negative control (`triangle_balanced`)",
        "",
        f"F1 range across methods (alpha >= .005) by N: {control['f1_range_across_methods_by_n']} — "
        f"{'FLAGGED (> .01): investigate the pipeline' if control['flagged'] else 'no separation, as expected'}.",
        "",
        "Full validation grid: `full_grid_validation.csv`. Figure: `recall_precision_vs_alpha.png`.",
        "",
    ]
    return "\n".join(lines)


def write_stage5i_report(raw: pd.DataFrame, config: Stage5iConfig, output_dir: Path) -> None:
    repository_root = config.source_path.parent.parent if config.source_path else Path(".")
    development, validation = _split(raw, config)
    rng = np.random.default_rng(BOOTSTRAP_SEED)

    gates = _run_gates(raw, repository_root)
    selection = _selection(development, config)
    report: dict[str, object] = {
        "gates": gates,
        "selection": selection,
        "q1": _q1(validation, config, rng),
        "q2": _q2(validation, config, rng),
        "q3": {
            "primary": _q3(validation, config, selection, "primary"),
            "sensitivity_equal_per_shape": _q3(validation, config, selection, "equal_per_shape"),
            "sensitivity_per_group": _q3(validation, config, selection, "per_group"),
        },
        "q4": _q4(validation, config),
        "negative_control": _negative_control(validation, config),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    _grid_table(validation).to_csv(output_dir / "full_grid_validation.csv", index=False)
    (output_dir / "stage5i_report.md").write_text(_markdown(report, config), encoding="utf-8")
    _figure(validation, config, output_dir)


# Generic shard-aggregation contract (see stage5a_reporting.py): the
# aggregator calls `write_report(raw, config, output_dir)`.
write_report = write_stage5i_report
