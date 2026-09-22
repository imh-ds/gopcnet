"""Report for the frozen Stage 6a edge-evidence-tier / bridge-inference
validation charter. See docs/stage6a_charter.md.

Computes G1 (pipeline-integrity gate), Q1-Q5 (descriptive, no gate) on
validation replicates only, plus the bootstrap calibration check at one
representative cell, and writes `stage6a_report.md`, `report.json`,
`full_grid_validation.csv`, and the false-confirmation-rate-vs-N figure.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from gopcnet.dpi.multi_conditional import compute_partial_correlation_evidence
from gopcnet.experiments.stage1j_fit import fit_candidate_forms, select_form
from gopcnet.experiments.stage6a import Stage6aConfig, screen_candidate_graph
from gopcnet.simulation.bridges import (
    build_shape_covariance,
    make_shape,
    observed_candidates,
    observed_true_bridges,
    sample_shape,
)

G1_THRESHOLD = 0.95
CONFIRMED_THRESHOLD = 1.0  # a pair is "confirmed" iff its survival fraction equals this
Q1_MARGIN = 0.20
Q1_CELL_FRACTION = 0.80
Q3_SHRINK_RATIO = 3.0
Q3_FLAT_RATIO = 1.5


def _split(raw: pd.DataFrame, config: Stage6aConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    ok = raw[raw["status"] == "ok"]
    dev_lo, dev_hi = config.development_replicates
    val_lo, val_hi = config.validation_replicates
    development = ok[(ok["replicate"] >= dev_lo) & (ok["replicate"] <= dev_hi)]
    validation = ok[(ok["replicate"] >= val_lo) & (ok["replicate"] <= val_hi)]
    return development, validation


def _cell_key(frame: pd.DataFrame) -> pd.core.groupby.generic.DataFrameGroupBy:
    return frame.groupby(["shape", "rho_bridge", "rho_confound", "n", "replicate"])


# --- G1: survival-fraction vs pMax top-1 agreement -------------------------


def _top1_by(group: pd.DataFrame, column: str, ascending: bool) -> str:
    ordered = group.sort_values(column, ascending=ascending, kind="stable")
    return str(ordered.iloc[0]["pair"])


def compute_g1(validation: pd.DataFrame) -> dict[str, object]:
    cell = validation[validation["shape"] == "confound_trap_observed"]
    agreements: list[bool] = []
    per_grid: dict[str, dict[str, float]] = {}
    for (rho_bridge, rho_confound, n), group in cell.groupby(["rho_bridge", "rho_confound", "n"]):
        matches = 0
        total = 0
        for _, replicate_group in group.groupby("replicate"):
            surv_pick = _top1_by(replicate_group, "surv", ascending=False)
            maxp_pick = _top1_by(replicate_group, "maxp", ascending=True)
            matches += int(surv_pick == maxp_pick)
            total += 1
        agreements.extend([matches / total] * total if total else [])
        per_grid[f"{rho_bridge:g}|{rho_confound:g}|{n}"] = matches / total if total else float("nan")
    fraction = float(np.mean(list(per_grid.values()))) if per_grid else float("nan")
    worst_cell = min(per_grid, key=lambda key: per_grid[key]) if per_grid else None
    return {
        "passed": bool(fraction >= G1_THRESHOLD) if per_grid else False,
        "mean_agreement_fraction": fraction,
        "worst_cell": worst_cell,
        "worst_cell_fraction": per_grid.get(worst_cell) if worst_cell else None,
        "per_cell_agreement": per_grid,
    }


# --- shared helpers ----------------------------------------------------------


def _hit_flags(group: pd.DataFrame, true_pairs: set[str], column: str, ascending: bool, slack: int) -> bool:
    n_bridges = max(len(true_pairs), 1)
    top_k = n_bridges + slack
    ordered = group.sort_values(column, ascending=ascending, kind="stable")
    top_set = set(ordered.iloc[:top_k]["pair"])
    return bool(true_pairs) and true_pairs <= top_set


def _exact_hit(group: pd.DataFrame, true_pairs: set[str], column: str, ascending: bool) -> bool:
    n_bridges = max(len(true_pairs), 1)
    ordered = group.sort_values(column, ascending=ascending, kind="stable")
    top_set = set(ordered.iloc[:n_bridges]["pair"])
    return bool(true_pairs) and true_pairs == top_set


SCORE_RULES = (("marg", False), ("surv", False), ("maxp", True))  # (column, ascending)


def _safe_nanmean(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or np.all(np.isnan(array)):
        return float("nan")
    return float(np.nanmean(array))


def _per_bridge_recovery(group: pd.DataFrame, true_pairs: set[str], column: str, ascending: bool, slack: int) -> float:
    """Fraction of individual true bridges (not the whole set) that land in
    the top n_bridges + slack ranked candidates."""
    if not true_pairs:
        return float("nan")
    n_bridges = len(true_pairs)
    ordered = group.sort_values(column, ascending=ascending, kind="stable")
    top_set = set(ordered.iloc[: n_bridges + slack]["pair"])
    return sum(1 for pair in true_pairs if pair in top_set) / n_bridges


def _true_pairs_for(shape_name: str, rho_bridge: float, rho_confound: float) -> set[str]:
    shape = make_shape(shape_name, rho_bridge, rho_confound)
    return {f"{i}-{j}" for i, j in observed_true_bridges(shape)}


def _grid_summary(validation: pd.DataFrame) -> pd.DataFrame:
    records = []
    for (shape_name, rho_bridge, rho_confound, n), cell in validation.groupby(["shape", "rho_bridge", "rho_confound", "n"]):
        true_pairs = _true_pairs_for(shape_name, rho_bridge, rho_confound)
        per_bridge = {column: [] for column, _ in SCORE_RULES}
        false_confirm_count, decoy_total = 0, 0
        bridge_confirmed_count, bridge_total = 0, 0
        for _, group in cell.groupby("replicate"):
            for column, ascending in SCORE_RULES:
                per_bridge[column].append(_per_bridge_recovery(group, true_pairs, column, ascending, slack=1))
            decoys = group[~group["pair"].isin(true_pairs)]
            confirmed = (~decoys["screened_out"].astype(bool)) & (decoys["surv"] >= CONFIRMED_THRESHOLD)
            false_confirm_count += int(confirmed.sum())
            decoy_total += len(decoys)
            bridges = group[group["pair"].isin(true_pairs)]
            confirmed_bridges = (~bridges["screened_out"].astype(bool)) & (bridges["surv"] >= CONFIRMED_THRESHOLD)
            bridge_confirmed_count += int(confirmed_bridges.sum())
            bridge_total += len(bridges)
        records.append(
            {
                "shape": shape_name,
                "rho_bridge": rho_bridge,
                "rho_confound": rho_confound,
                "n": n,
                "n_true_bridges": len(true_pairs),
                "recovery_marg": _safe_nanmean(per_bridge["marg"]),
                "recovery_surv": _safe_nanmean(per_bridge["surv"]),
                "recovery_maxp": _safe_nanmean(per_bridge["maxp"]),
                "false_confirm_rate": false_confirm_count / decoy_total if decoy_total else float("nan"),
                "bridge_confirmed_rate": bridge_confirmed_count / bridge_total if bridge_total else float("nan"),
            }
        )
    return pd.DataFrame.from_records(records)


def _exact_joint_recovery(validation: pd.DataFrame, shape_name: str) -> pd.DataFrame:
    records = []
    for (rho_bridge, rho_confound, n), cell in validation[validation["shape"] == shape_name].groupby(
        ["rho_bridge", "rho_confound", "n"]
    ):
        true_pairs = _true_pairs_for(shape_name, rho_bridge, rho_confound)
        hits = {column: 0 for column, _ in SCORE_RULES}
        total = 0
        for _, group in cell.groupby("replicate"):
            for column, ascending in SCORE_RULES:
                hits[column] += int(_exact_hit(group, true_pairs, column, ascending))
            total += 1
        records.append(
            {
                "rho_bridge": rho_bridge,
                "rho_confound": rho_confound,
                "n": n,
                **{f"exact_joint_{column}": hits[column] / total if total else float("nan") for column, _ in SCORE_RULES},
            }
        )
    return pd.DataFrame.from_records(records)


# --- Q1-Q5 ------------------------------------------------------------------


def compute_q1(grid: pd.DataFrame) -> dict[str, object]:
    cells = grid[(grid["shape"] == "confound_trap_observed") & (grid["n_true_bridges"] > 0)]
    margin_met = (cells["recovery_surv"] - cells["recovery_marg"]) >= Q1_MARGIN
    fraction = float(margin_met.mean()) if len(cells) else float("nan")
    return {
        "cells_meeting_margin": int(margin_met.sum()),
        "total_cells": int(len(cells)),
        "fraction_meeting_margin": fraction,
        "confirms_preliminary_finding": bool(fraction >= Q1_CELL_FRACTION) if len(cells) else False,
        "per_cell": cells[["rho_bridge", "rho_confound", "n", "recovery_marg", "recovery_surv"]].to_dict("records"),
    }


def compute_q2(grid: pd.DataFrame) -> dict[str, object]:
    monotonic_by_shape = {}
    for shape_name, shape_grid in grid.groupby("shape"):
        if shape_grid["n_true_bridges"].max() == 0:
            continue
        by_n = shape_grid.groupby("n")["recovery_surv"].mean().sort_index()
        diffs = by_n.diff().dropna()
        monotonic_by_shape[shape_name] = {
            "recovery_by_n": by_n.to_dict(),
            "monotonic_nondecreasing": bool((diffs >= -1e-9).all()),
        }
    return monotonic_by_shape


def compute_q3(grid: pd.DataFrame) -> dict[str, object]:
    out = {}
    for shape_name in ("confound_trap_observed", "confound_trap_latent"):
        shape_grid = grid[grid["shape"] == shape_name]
        by_n = shape_grid.groupby("n")["false_confirm_rate"].mean().sort_index()
        if len(by_n) < 2:
            out[shape_name] = {"false_confirm_rate_by_n": by_n.to_dict()}
            continue
        low_n, high_n = by_n.index.min(), by_n.index.max()
        ratio = (by_n.loc[low_n] / by_n.loc[high_n]) if by_n.loc[high_n] > 0 else float("inf")
        out[shape_name] = {
            "false_confirm_rate_by_n": by_n.to_dict(),
            "ratio_low_n_over_high_n": float(ratio),
        }
    observed_ratio = out.get("confound_trap_observed", {}).get("ratio_low_n_over_high_n", float("nan"))
    latent_ratio = out.get("confound_trap_latent", {}).get("ratio_low_n_over_high_n", float("nan"))
    observed_shrinks = observed_ratio >= Q3_SHRINK_RATIO
    latent_flat = latent_ratio <= Q3_FLAT_RATIO
    out["verdict"] = (
        "confirms the disclosed limitation (measured confound shrinks, unmeasured confound stays flat)"
        if observed_shrinks and latent_flat
        else "does not match the predeclared pattern -- limitation restated per the actual result"
    )
    return out


def compute_q4(grid: pd.DataFrame) -> dict[str, object]:
    small = grid[(grid["shape"] == "confound_trap_observed") & (grid["n_true_bridges"] > 0)]
    large = grid[(grid["shape"] == "larger_clusters") & (grid["n_true_bridges"] > 0)]
    merged = small.merge(large, on=["rho_bridge", "rho_confound", "n"], suffixes=("_small", "_large"))
    merged["recovery_diff_large_minus_small"] = merged["recovery_surv_large"] - merged["recovery_surv_small"]
    return {
        "mean_recovery_diff": float(merged["recovery_diff_large_minus_small"].mean()) if len(merged) else float("nan"),
        "per_cell": merged[["rho_bridge", "rho_confound", "n", "recovery_surv_small", "recovery_surv_large", "recovery_diff_large_minus_small"]].to_dict("records"),
        "note": "larger_clusters uses RHO_WITHIN_LARGE_CLUSTER=0.25 vs 0.30 for confound_trap_observed (implementation-time amendment, see charter) -- direct comparison is disclosed, not a clean ceteris-paribus contrast.",
    }


def compute_q5(grid: pd.DataFrame, validation: pd.DataFrame) -> dict[str, object]:
    double = grid[grid["shape"] == "double_bridge"]
    single = grid[grid["shape"] == "confound_trap_observed"]
    merged = double.merge(single, on=["rho_bridge", "rho_confound", "n"], suffixes=("_double", "_single"))
    exact = _exact_joint_recovery(validation, "double_bridge")
    return {
        "per_bridge_recovery_vs_single_bridge_shape": merged[
            ["rho_bridge", "rho_confound", "n", "recovery_surv_double", "recovery_surv_single"]
        ].to_dict("records"),
        "exact_joint_recovery": exact.to_dict("records"),
    }


# --- bootstrap calibration ---------------------------------------------------


def bootstrap_calibration(config: Stage6aConfig) -> dict[str, object]:
    shape_observed = make_shape("confound_trap_observed", config.bootstrap_rho_bridge, config.bootstrap_rho_confound)
    shape_latent = make_shape("confound_trap_latent", config.bootstrap_rho_bridge, config.bootstrap_rho_confound)
    alpha_prune = select_form(fit_candidate_forms()).predict(float(config.bootstrap_n))
    rng = np.random.default_rng(hash(("stage6a_bootstrap", config.bootstrap_rho_bridge, config.bootstrap_rho_confound)) % 2**31)

    results = {}
    for label, shape in (("confound_trap_observed", shape_observed), ("confound_trap_latent", shape_latent)):
        covariance = build_shape_covariance(shape)
        candidates = observed_candidates(shape)
        true_pairs = set(observed_true_bridges(shape))
        confound_decoy = next(((i, j) for i, j in candidates if (i, j) not in true_pairs and _is_confound_decoy(shape, i, j)), None)
        bridge_rates, decoy_rates = [], []
        for _ in range(config.bootstrap_replicates):
            data = sample_shape(shape, config.bootstrap_n, rng, covariance=covariance)
            bridge_confirmed = 0
            decoy_confirmed = 0
            for _ in range(config.bootstrap_resamples):
                idx = rng.integers(0, config.bootstrap_n, config.bootstrap_n)
                resampled = data[idx]
                candidate_graph = screen_candidate_graph(resampled, config.screening_alpha)
                for pair, counter_name in ((next(iter(true_pairs)), "bridge"), (confound_decoy, "decoy")):
                    if pair is None:
                        continue
                    i, j = pair
                    if not candidate_graph[i, j]:
                        continue
                    pool = sorted((set(np.flatnonzero(candidate_graph[i])) | set(np.flatnonzero(candidate_graph[j]))) - {i, j})
                    from gopcnet.experiments.stage6a import profile_pair

                    survival, _ = profile_pair(resampled, i, j, pool, alpha_prune, config.max_conditioning_size)
                    if survival >= CONFIRMED_THRESHOLD:
                        if counter_name == "bridge":
                            bridge_confirmed += 1
                        else:
                            decoy_confirmed += 1
            bridge_rates.append(bridge_confirmed / config.bootstrap_resamples)
            decoy_rates.append(decoy_confirmed / config.bootstrap_resamples)
        results[label] = {
            "mean_bridge_confirmed_rate": float(np.mean(bridge_rates)),
            "mean_decoy_confirmed_rate": float(np.mean(decoy_rates)),
            "correctly_ordered": bool(np.mean(bridge_rates) > np.mean(decoy_rates)),
        }
    return results


def _is_confound_decoy(shape, i: int, j: int) -> bool:
    """Identify the pair whose only path is through a shared third node
    (the confound) rather than a direct edge between i and j."""
    direct_edges = {(a, b) for a, b, _ in shape.edges} | {(b, a) for a, b, _ in shape.edges}
    if (i, j) in direct_edges:
        return False
    edge_partners: dict[int, set[int]] = {}
    for a, b, _ in shape.edges:
        edge_partners.setdefault(a, set()).add(b)
        edge_partners.setdefault(b, set()).add(a)
    return len(edge_partners.get(i, set()) & edge_partners.get(j, set())) > 0


# --- output ------------------------------------------------------------------


def _figure(grid: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for shape_name, style in (("confound_trap_observed", "-o"), ("confound_trap_latent", "--s")):
        by_n = grid[grid["shape"] == shape_name].groupby("n")["false_confirm_rate"].mean().sort_index()
        ax.plot(by_n.index, by_n.values, style, label=shape_name)
    ax.set_xlabel("N")
    ax.set_ylabel("false-confirmation rate on decoys")
    ax.set_title("Confound measured vs. unmeasured: false-bridge rate vs. N")
    ax.legend()
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(output_dir / "false_confirm_rate_vs_n.png", dpi=130)
    plt.close(fig)


def _markdown(report: dict[str, object]) -> str:
    lines = ["# Stage 6a report: edge-evidence tiers and bridge inference", ""]
    lines += ["Charter: `docs/stage6a_charter.md` (FROZEN before results). All comparisons use validation replicates only.", ""]
    g1 = report["g1"]
    lines += [
        "## G1 (pipeline integrity)",
        "",
        f"- **G1**: {'PASSED' if g1['passed'] else 'FAILED'} -- mean survival-vs-pMax top-1 agreement "
        f"{g1['mean_agreement_fraction']:.4f} (threshold {G1_THRESHOLD}); worst cell {g1['worst_cell']} at "
        f"{g1['worst_cell_fraction']}",
        "",
        "## Q1 -- survival-fraction ranking vs marginal-correlation ranking",
        "",
        f"{report['q1']['cells_meeting_margin']} of {report['q1']['total_cells']} cells meet the >= .20 margin "
        f"({report['q1']['fraction_meeting_margin']:.2f} fraction, threshold {Q1_CELL_FRACTION}): "
        f"**{'confirms' if report['q1']['confirms_preliminary_finding'] else 'does not confirm'}** the preliminary scratch finding.",
        "",
        "## Q2 -- does detection power scale with N and bridge strength as expected?",
        "",
    ]
    for shape_name, info in report["q2"].items():
        lines.append(f"- **{shape_name}**: monotonic non-decreasing in N: {info['monotonic_nondecreasing']} ({info['recovery_by_n']})")
    lines += ["", "## Q3 -- does the false-confirmation rate behave as predicted?", ""]
    for shape_name in ("confound_trap_observed", "confound_trap_latent"):
        info = report["q3"].get(shape_name, {})
        lines.append(f"- **{shape_name}**: {info.get('false_confirm_rate_by_n')}, ratio (low N / high N) = {info.get('ratio_low_n_over_high_n')}")
    lines.append(f"- **Verdict**: {report['q3']['verdict']}")
    lines += ["", "## Q4 -- does a larger conditioning pool degrade detection?", ""]
    lines.append(f"Mean recovery difference (larger_clusters minus confound_trap_observed): {report['q4']['mean_recovery_diff']:.4f}")
    lines.append(report["q4"]["note"])
    lines += ["", "## Q5 -- double_bridge joint recovery", ""]
    lines.append(f"Per-bridge recovery vs. single-bridge shape and exact-joint recovery are in `report.json`.")
    lines += ["", "## Bootstrap calibration", ""]
    for label, info in report["bootstrap_calibration"].items():
        lines.append(
            f"- **{label}**: bridge confirmed rate {info['mean_bridge_confirmed_rate']:.2f}, "
            f"decoy confirmed rate {info['mean_decoy_confirmed_rate']:.2f}, correctly ordered: {info['correctly_ordered']}"
        )
    lines += ["", "Full validation grid: `full_grid_validation.csv`. Figure: `false_confirm_rate_vs_n.png`.", ""]
    return "\n".join(lines)


def write_stage6a_report(raw: pd.DataFrame, config: Stage6aConfig, output_dir: Path) -> None:
    _, validation = _split(raw, config)
    grid = _grid_summary(validation)

    report = {
        "g1": compute_g1(validation),
        "q1": compute_q1(grid),
        "q2": compute_q2(grid),
        "q3": compute_q3(grid),
        "q4": compute_q4(grid),
        "q5": compute_q5(grid, validation),
        "bootstrap_calibration": bootstrap_calibration(config),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    grid.to_csv(output_dir / "full_grid_validation.csv", index=False)
    (output_dir / "stage6a_report.md").write_text(_markdown(report), encoding="utf-8")
    _figure(grid, output_dir)


write_report = write_stage6a_report  # generic shard-aggregation contract
