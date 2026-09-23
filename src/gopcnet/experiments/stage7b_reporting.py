"""Report for Stage 7b (docs/stage7b_charter.md).

Gates G1-G3, then Q1-Q7 on validation replicates, with verdicts counted
within each structure over its cells with `N >= 500`, `N = 250` reported
separately, and the charter's predeclared routing (A/B/C/D/mixed). Every
threshold is the charter's.

Operationalization notes (fixed here before any full run):

- **Q1 trend** (D-050's classification): over increasing `N`, a series
  is "increasing" if every step is `>= -.01` and the total change is
  `> .01`, "decreasing" if every step is `<= .01` and the total change is
  `< -.01`, "flat" if the total change is within `.01` in absolute value,
  and otherwise "non-monotone".
- **Paired differences** use replicates where both methods have a
  defined value for the metric. The count of excluded pairs is reported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gopcnet.experiments.stage7b import ANCHOR, ANCHOR_METHOD, Stage7bConfig

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 702
G1_ROW_FRACTION = 0.999
G3_MAX_Z = 3.0
Q2_PRECISION_MARGIN = 0.05
Q2_F1_MARGIN = -0.02
Q3_TOLERANCE = 0.01
Q4_TOLERANCE = 0.01
Q6_SHARE = 0.75
MIN_COUNTED_N = 500
STAGE5G_ARCHIVE = Path("evidence/stage5_benchmarks/stage5g_growing_subset/raw_metrics.csv")


def _validation(raw: pd.DataFrame, config: Stage7bConfig) -> pd.DataFrame:
    low, high = config.validation_replicates
    return raw[(raw["replicate"] >= low) & (raw["replicate"] <= high) & (raw["status"] == "ok")]


def _development(raw: pd.DataFrame, config: Stage7bConfig) -> pd.DataFrame:
    low, high = config.development_replicates
    return raw[(raw["replicate"] >= low) & (raw["replicate"] <= high) & (raw["status"] == "ok")]


def _paired(frame: pd.DataFrame, metric: str, a: str, b: str) -> np.ndarray:
    wide = frame[frame["method"].isin([a, b])].pivot_table(
        index="replicate", columns="method", values=metric, aggfunc="first"
    )
    if a not in wide or b not in wide:
        return np.array([])
    return (wide[a] - wide[b]).dropna().to_numpy()


def _ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    draws = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[draws].mean(axis=1)
    return float(values.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _psych(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["structure"] != ANCHOR]


# --- gates ---------------------------------------------------------------


def gate_g1(raw: pd.DataFrame) -> dict[str, Any]:
    subset = raw[raw["method"].isin(["pc@0.01", "pc_frozen@0.01"]) & (raw["status"] == "ok")]
    wide = subset.pivot_table(
        index=["structure", "p", "n", "replicate"], columns="method", values="edge_bits", aggfunc="first"
    ).dropna()
    if wide.empty:
        return {"passed": None, "rows_compared": 0, "identical_fraction": None}
    identical = float((wide["pc@0.01"] == wide["pc_frozen@0.01"]).mean())
    return {"passed": identical >= G1_ROW_FRACTION, "rows_compared": int(len(wide)), "identical_fraction": identical}


def gate_g2(raw: pd.DataFrame) -> dict[str, Any]:
    psych = _psych(raw)
    hashes = psych[psych["truth_hash"].astype(str) != ""].groupby(["structure", "p", "replicate"])["truth_hash"]
    unpaired = int((hashes.nunique() > 1).sum())
    return {"passed": unpaired == 0, "truths_checked": int(hashes.ngroups), "truths_differing_across_n": unpaired}


def gate_g3(raw: pd.DataFrame, repository_root: Path) -> dict[str, Any]:
    anchor = raw[(raw["method"] == ANCHOR_METHOD) & (raw["status"] == "ok")]
    archive_path = repository_root / STAGE5G_ARCHIVE
    if anchor.empty or not archive_path.is_file():
        return {"passed": None, "reason": "no anchor rows or archive missing"}
    archive = pd.read_csv(archive_path)
    archive = archive[(archive["dgp"] == "chain_fork_hub") & (archive["method"] == "gopc_growing_subset")]
    cells, passed = [], True
    for n, frame in anchor.groupby("n"):
        reference = archive[archive["n"] == n]
        cell: dict[str, Any] = {"n": int(n)}
        for metric in ("precision", "recall"):
            ours = frame["precision" if metric == "precision" else "sensitivity"].dropna()
            theirs = reference[metric].dropna()
            se = np.sqrt(ours.var(ddof=1) / len(ours) + theirs.var(ddof=1) / len(theirs))
            z = float((ours.mean() - theirs.mean()) / se) if se > 0 else 0.0
            cell[f"{metric}_ours"], cell[f"{metric}_archive"], cell[f"{metric}_z"] = (
                float(ours.mean()),
                float(theirs.mean()),
                z,
            )
            passed = passed and abs(z) <= G3_MAX_Z
        merged = frame.merge(reference[["replicate", "seed"]], on=["replicate", "seed"], how="inner")
        cell["rows_with_identical_seed"] = int(len(merged))
        cells.append(cell)
    return {"passed": passed, "cells": cells, "max_abs_z": G3_MAX_Z}


# --- questions -----------------------------------------------------------


def _trend(values: list[float]) -> str:
    steps = np.diff(values)
    total = values[-1] - values[0]
    if np.all(steps >= -0.01) and total > 0.01:
        return "increasing"
    if np.all(steps <= 0.01) and total < -0.01:
        return "decreasing"
    if abs(total) <= 0.01:
        return "flat"
    return "non-monotone"


def question_1(validation: pd.DataFrame) -> list[dict[str, Any]]:
    ebic = _psych(validation[validation["method"] == "ebicglasso"])
    rows = []
    for (structure, p), frame in ebic.groupby(["structure", "p"]):
        by_n = frame.groupby("n")[["precision", "specificity"]].mean().sort_index()
        rows.append(
            {
                "structure": structure,
                "p": int(p),
                "precision_by_n": {int(k): float(v) for k, v in by_n["precision"].items()},
                "specificity_by_n": {int(k): float(v) for k, v in by_n["specificity"].items()},
                "precision_trend": _trend(by_n["precision"].tolist()),
            }
        )
    return rows


def _cell_groups(validation: pd.DataFrame):
    return _psych(validation).groupby(["structure", "p", "n"])


def question_2(validation: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    cells = []
    for (structure, p, n), frame in _cell_groups(validation):
        precision = _ci(_paired(frame, "precision", "gopc", "ebicglasso"), rng)
        f1 = _ci(_paired(frame, "f1", "gopc", "ebicglasso"), rng)
        supports = precision[1] > Q2_PRECISION_MARGIN and f1[1] >= Q2_F1_MARGIN
        cells.append(
            {"structure": structure, "p": int(p), "n": int(n), "precision_diff": precision, "f1_diff": f1,
             "supports_niche": bool(supports)}
        )  # fmt: skip
    verdicts = {}
    for structure in sorted({c["structure"] for c in cells}):
        counted = [c for c in cells if c["structure"] == structure and c["n"] >= MIN_COUNTED_N]
        k = sum(c["supports_niche"] for c in counted)
        verdict = "HOLDS" if k >= 7 else "PARTIAL" if k >= 3 else "FAILS"
        verdicts[structure] = {"cells_supporting": k, "cells_counted": len(counted), "verdict": verdict}
    return {"cells": cells, "verdicts": verdicts}


def _classify(ci: tuple[float, float, float], tolerance: float) -> str:
    _, low, high = ci
    if np.isnan(low):
        return "n/a"
    if low > tolerance:
        return "better"
    if high < -tolerance:
        return "worse"
    return "comparable"


def question_3(validation: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    cells = []
    for (structure, p, n), frame in _cell_groups(validation):
        cell: dict[str, Any] = {"structure": structure, "p": int(p), "n": int(n)}
        for comparator in ("nonreg_holm", "nonreg_bh"):
            ci = _ci(_paired(frame, "mcc", "gopc", comparator), rng)
            cell[f"vs_{comparator}"] = {"mcc_diff": ci, "class": _classify(ci, Q3_TOLERANCE)}
        cells.append(cell)
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for cell in cells:
        if cell["n"] < MIN_COUNTED_N:
            continue
        for comparator in ("nonreg_holm", "nonreg_bh"):
            bucket = counts.setdefault(cell["structure"], {}).setdefault(comparator, {})
            label = cell[f"vs_{comparator}"]["class"]
            bucket[label] = bucket.get(label, 0) + 1
    return {"cells": cells, "counts": counts}


def question_4(development: pd.DataFrame, validation: pd.DataFrame, config: Stage7bConfig, rng) -> dict[str, Any]:
    pc_methods = [f"pc@{alpha:g}" for alpha in config.pc_alphas]
    assert set(development["replicate"]).isdisjoint(set(validation["replicate"])), "dev/val overlap"
    selected = {}
    for n, frame in _psych(development).groupby("n"):
        scores = (
            frame[frame["method"].isin(pc_methods)]
            .groupby(["method", "structure", "p"])["mcc"]
            .mean()
            .groupby("method")
            .mean()
        )
        selected[int(n)] = str(scores.idxmax())
    per_n = {}
    for n, frame in _psych(validation).groupby("n"):
        n = int(n)
        pc_selected = selected.get(n)
        pc_ok = gopc_ok = total = 0
        any_alpha_everywhere = False
        combos = list(frame.groupby(["structure", "p"]))
        for structure_p, cell in combos:
            total += 1
            ci_pc = _ci(_paired(cell, "mcc", pc_selected, "gopc"), rng)
            ci_gopc = _ci(_paired(cell, "mcc", "gopc", pc_selected), rng)
            pc_ok += int(ci_pc[1] >= -Q4_TOLERANCE)
            gopc_ok += int(ci_gopc[1] >= -Q4_TOLERANCE)
        for method in pc_methods:
            if all(_ci(_paired(cell, "mcc", method, "gopc"), rng)[1] >= -Q4_TOLERANCE for _, cell in combos):
                any_alpha_everywhere = True
        per_n[n] = {
            "selected_pc": pc_selected,
            "cells": total,
            "pc_selected_comparable_or_better": pc_ok,
            "gopc_comparable_or_better": gopc_ok,
            "some_single_pc_alpha_matches_everywhere": any_alpha_everywhere,
        }
    counted = [v for n, v in per_n.items()]
    replicates = sum(
        (not v["some_single_pc_alpha_matches_everywhere"]) and v["gopc_comparable_or_better"] >= 0.8 * v["cells"]
        for v in counted
    ) >= 3
    return {"selected_by_n": selected, "per_n": per_n, "verdict": "REPLICATES" if replicates else "DOES NOT REPLICATE"}


def question_5(validation: pd.DataFrame) -> dict[str, Any]:
    gopc = _psych(validation[validation["method"] == "gopc"])
    table = (
        gopc.groupby(["structure", "p", "n"])[["screen_pass_fraction", "null_removed_by_screen", "null_removed_by_prune"]]
        .mean()
        .reset_index()
    )
    no_isolates = table[(table["structure"] != "random_with_isolates") & (table["n"] >= 1000)]
    isolates = table[table["structure"] == "random_with_isolates"]
    prediction_1 = bool((no_isolates["null_removed_by_screen"] < 0.5).all()) if len(no_isolates) else None
    prediction_2 = (
        bool(isolates["null_removed_by_screen"].mean() > table[table["structure"] != "random_with_isolates"][
            "null_removed_by_screen"
        ].mean())
        if len(isolates)
        else None
    )
    return {
        "table": table.to_dict(orient="records"),
        "prediction_screen_minor_without_isolates": prediction_1,
        "prediction_screen_larger_with_isolates": prediction_2,
    }


def question_6(validation: pd.DataFrame, rng: np.random.Generator) -> dict[str, Any]:
    gopc = _psych(validation[validation["method"] == "gopc"])
    cells, favourable = [], 0
    for (structure, p, n), frame in gopc.groupby(["structure", "p", "n"]):
        diff = (frame["weight_mae_refit"] - frame["weight_mae_native"]).dropna().to_numpy()
        ci = _ci(diff, rng)
        refit_better = bool(ci[2] < 0)
        cells.append({"structure": structure, "p": int(p), "n": int(n), "mae_refit_minus_native": ci,
                      "refit_better": refit_better})  # fmt: skip
    counted = [c for c in cells if c["n"] >= MIN_COUNTED_N]
    favourable = sum(c["refit_better"] for c in counted)
    share = favourable / len(counted) if counted else float("nan")
    return {"cells": cells, "share_refit_better": share, "verdict": "RECOMMEND REFIT" if share >= Q6_SHARE else "KEEP MIN_SUBSET"}


def question_7(raw: pd.DataFrame) -> list[dict[str, Any]]:
    ok = _psych(raw[raw["status"] == "ok"])
    table = ok.groupby(["method", "p", "n"])["elapsed_seconds"].agg(["median", lambda s: s.quantile(0.9)])
    table.columns = ["median_seconds", "p90_seconds"]
    return table.reset_index().to_dict(orient="records")


def routing(q2: dict[str, Any], q3: dict[str, Any]) -> str:
    verdicts = q2["verdicts"]
    non_isolate = [s for s in verdicts if s != "random_with_isolates"]
    holds = sum(verdicts[s]["verdict"] == "HOLDS" for s in non_isolate)
    fails = sum(verdicts[s]["verdict"] == "FAILS" for s in verdicts)

    def majority_worse(comparator: str, structure: str) -> bool:
        bucket = q3["counts"].get(structure, {}).get(comparator, {})
        return bucket.get("worse", 0) > sum(bucket.values()) / 2

    structures_worse = {
        comparator: sum(majority_worse(comparator, s) for s in verdicts) for comparator in ("nonreg_holm", "nonreg_bh")
    }
    if holds >= 3 and not any(majority_worse(c, s) for c in ("nonreg_holm", "nonreg_bh") for s in verdicts):
        return "A"
    if max(structures_worse.values()) >= 3:
        return "C"
    isolates = verdicts.get("random_with_isolates", {}).get("verdict")
    if fails >= 3 and isolates == "FAILS":
        return "D"
    if isolates in ("HOLDS", "PARTIAL") and sum(verdicts[s]["verdict"] == "FAILS" for s in non_isolate) > len(
        non_isolate
    ) / 2:
        return "B"
    return "mixed"


# --- output ----------------------------------------------------------------


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def _figures(raw: pd.DataFrame, validation: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    psych = _psych(validation)
    main_methods = ["gopc", "ebicglasso", "nonreg_holm", "nonreg_bh", "pc@0.01"]
    structures = sorted(psych["structure"].unique())
    ps = sorted(psych["p"].unique())
    if structures and ps:
        fig, axes = plt.subplots(len(structures), len(ps), figsize=(3.2 * len(ps), 2.4 * len(structures)), squeeze=False)
        for i, structure in enumerate(structures):
            for j, p in enumerate(ps):
                axis = axes[i][j]
                cell = psych[(psych["structure"] == structure) & (psych["p"] == p)]
                for method in main_methods:
                    series = cell[cell["method"] == method].groupby("n")["precision"].mean()
                    if len(series):
                        axis.plot(series.index, series.values, marker="o", markersize=3, label=method)
                axis.set_title(f"{structure}, p={p}", fontsize=8)
                axis.set_ylim(0, 1.02)
                axis.tick_params(labelsize=7)
        axes[0][0].legend(fontsize=6)
        fig.suptitle("Stage 7b: precision vs N (validation replicates)")
        fig.tight_layout()
        fig.savefig(output_dir / "precision_vs_n.png", dpi=130)
        plt.close(fig)
        fig, axis = plt.subplots(figsize=(6, 5))
        summary = psych[psych["method"].isin(main_methods)].groupby(["method", "structure", "p", "n"])[
            ["sensitivity", "specificity"]
        ].mean()
        for method, group in summary.groupby(level="method"):
            axis.scatter(group["specificity"], group["sensitivity"], s=10, label=method, alpha=0.7)
        axis.set_xlabel("specificity")
        axis.set_ylabel("sensitivity")
        axis.legend(fontsize=7)
        axis.set_title("Stage 7b: sensitivity vs specificity per cell")
        fig.tight_layout()
        fig.savefig(output_dir / "sensitivity_vs_specificity.png", dpi=130)
        plt.close(fig)
        truths = _psych(raw[raw["method"] == "gopc"]).drop_duplicates(["structure", "p", "replicate"])
        fig, axis = plt.subplots(figsize=(7, 4))
        labels, data = [], []
        for (structure, p), frame in truths.groupby(["structure", "p"]):
            labels.append(f"{structure}\np={p}")
            data.append(frame["true_mean_abs_weight"].dropna().to_numpy())
        axis.boxplot(data)
        axis.set_xticks(range(1, len(labels) + 1), labels)  # works on matplotlib 3.8 and 3.9+
        axis.tick_params(axis="x", labelsize=5, rotation=90)
        axis.set_ylabel("mean |true partial correlation|")
        axis.set_title("Stage 7b: realized truth strength by structure (PD shrinkage)")
        fig.tight_layout()
        fig.savefig(output_dir / "truth_strength.png", dpi=130)
        plt.close(fig)


def write_stage7b_report(raw: pd.DataFrame, config: Stage7bConfig, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    repository_root = (
        config.source_path.parent.parent if config.source_path is not None else Path(__file__).resolve().parents[3]
    )
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    validation = _validation(raw, config)
    development = _development(raw, config)
    report: dict[str, Any] = {
        "g1": gate_g1(raw),
        "g2": gate_g2(raw),
        "g3": gate_g3(raw, repository_root),
        "q1": question_1(validation),
        "q2": question_2(validation, rng),
        "q3": question_3(validation, rng),
        "q4": question_4(development, validation, config, rng),
        "q5": question_5(validation),
        "q6": question_6(validation, rng),
        "q7": question_7(raw),
        "status_counts": raw.groupby(["method", "status"]).size().rename("rows").reset_index().to_dict("records"),
    }
    report["routing"] = routing(report["q2"], report["q3"])
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    _figures(raw, validation, output_dir)

    g1, g2, g3 = report["g1"], report["g2"], report["g3"]
    lines = [
        "# Stage 7b report: external validity",
        "",
        "Charter: `docs/stage7b_charter.md`. Questions use validation replicates; verdict counts use cells with "
        f"N >= {MIN_COUNTED_N} (N = 250 is characterization only).",
        "",
        "## Gates",
        "",
        f"- **G1**: {g1['passed']} -- identical fraction {_fmt(g1['identical_fraction'], 4)} over {g1['rows_compared']} rows.",
        f"- **G2**: {g2['passed']} -- {g2['truths_differing_across_n']} of {g2['truths_checked']} truths differ across N.",
        f"- **G3**: {g3.get('passed')} -- {json.dumps(g3.get('cells', g3.get('reason')))}",
        "",
        f"## Routing outcome: **{report['routing']}**",
        "",
        "## Q2 -- GOPC vs EBICglasso (niche claim)",
        "",
    ]
    for structure, verdict in report["q2"]["verdicts"].items():
        lines.append(f"- **{structure}**: {verdict['verdict']} ({verdict['cells_supporting']}/{verdict['cells_counted']})")
    lines += ["", "| structure | p | N | precision diff [CI] | F1 diff [CI] | supports |", "|---|---|---|---|---|---|"]
    for cell in report["q2"]["cells"]:
        pd_, f1 = cell["precision_diff"], cell["f1_diff"]
        lines.append(
            f"| {cell['structure']} | {cell['p']} | {cell['n']} | {_fmt(pd_[0])} [{_fmt(pd_[1])}, {_fmt(pd_[2])}] "
            f"| {_fmt(f1[0])} [{_fmt(f1[1])}, {_fmt(f1[2])}] | {cell['supports_niche']} |"
        )
    lines += ["", "## Q1 -- EBICglasso precision by N", "", "| structure | p | precision by N | trend |", "|---|---|---|---|"]
    for row in report["q1"]:
        series = ", ".join(f"{n}: {v:.3f}" for n, v in row["precision_by_n"].items())
        lines.append(f"| {row['structure']} | {row['p']} | {series} | {row['precision_trend']} |")
    lines += ["", "## Q3 -- GOPC vs non-regularized (MCC)", ""]
    for structure, comparators in report["q3"]["counts"].items():
        lines.append(f"- **{structure}**: " + "; ".join(f"{c}: {dict(v)}" for c, v in comparators.items()))
    q4 = report["q4"]
    lines += ["", f"## Q4 -- one default vs one PC alpha: **{q4['verdict']}**", ""]
    for n, row in q4["per_n"].items():
        lines.append(f"- N={n}: {json.dumps(row)}")
    q5 = report["q5"]
    lines += [
        "",
        "## Q5 -- mechanism",
        "",
        f"- screen removes < 50% of true non-edges without isolates (N >= 1000): {q5['prediction_screen_minor_without_isolates']}",
        f"- screen's share larger with isolates: {q5['prediction_screen_larger_with_isolates']}",
        "",
        f"## Q6 -- weights: **{report['q6']['verdict']}** (refit better in {_fmt(report['q6']['share_refit_better'])} of counted cells)",
        "",
        "## Q7 -- runtime: see `report.json` (`q7`).",
        "",
        "Figures: `precision_vs_n.png`, `sensitivity_vs_specificity.png`, `truth_strength.png`.",
        "",
    ]
    (output_dir / "stage7b_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


write_report = write_stage7b_report
