"""Post hoc analyses behind D-071, computed from the archived Stage 7b raw
metrics (validation replicates 250-499 only). Not predeclared; descriptive.

Run from the repository root:

    py -3.11 evidence/stage7_external_validity/d071_posthoc/d071_posthoc.py

Writes, next to this script:

- `operating_points.csv`: mean sensitivity, specificity, precision and MCC
  per method, overall and by N.
- `fixed_setting_regret.csv`: per method, the MCC shortfall from the best
  compared method in each (structure, p, N) cell ("regret"), summarized
  over cells, for all N and for N >= 500.
- `recall_by_edge_strength.csv`: recall per method and N, by the true
  edge's absolute partial correlation (<.1, .1-.2, >=.2). Truths are
  regenerated from the frozen Stage 7b seeds.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from gopcnet.experiments import stage7b
from gopcnet.experiments.stage5i import decode_edges
from gopcnet.generators.psych_networks import make_truth

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / "evidence/stage7_external_validity/stage7b_benchmark/raw_metrics.csv.gz"
CONFIG = ROOT / "configs/stage7b_external_validity.yaml"

REGRET_METHODS = ["gopc", "pc@0.01", "pc@0.05", "nonreg_bh", "nonreg_holm", "ebicglasso"]
STRENGTH_METHODS = ["gopc", "pc@0.01", "pc@0.05", "nonreg_bh"]
STRENGTH_BINS = [(0.0, 0.1, "<.1"), (0.1, 0.2, ".1-.2"), (0.2, 1.0, ">=.2")]
CELL = ["structure", "p", "n"]


def load_validation() -> pd.DataFrame:
    raw = pd.read_csv(RAW)
    return raw[(raw.replicate >= 250) & (raw.structure != "anchor") & (raw.status == "ok")]


def operating_points(data: pd.DataFrame) -> pd.DataFrame:
    columns = ["sensitivity", "specificity", "precision", "mcc"]
    subset = data[data.method.isin(REGRET_METHODS)]
    overall = subset.groupby("method")[columns].mean().assign(n="all")
    by_n = subset.groupby(["method", "n"])[columns].mean().reset_index("n")
    by_n["n"] = by_n["n"].astype(str)
    return pd.concat([overall, by_n]).reset_index().round(4)


def fixed_setting_regret(data: pd.DataFrame) -> pd.DataFrame:
    cells = (
        data[data.method.isin(REGRET_METHODS)]
        .groupby(CELL + ["method"])[["mcc", "precision"]]
        .mean()
        .reset_index()
    )
    cells["regret"] = cells.groupby(CELL).mcc.transform("max") - cells.mcc
    frames = []
    for label, sizes in [("all", [250, 500, 1000, 2000]), ("n>=500", [500, 1000, 2000])]:
        summary = (
            cells[cells.n.isin(sizes)]
            .groupby("method")
            .agg(
                mean_regret=("regret", "mean"),
                worst_regret=("regret", "max"),
                min_cell_precision=("precision", "min"),
                best_in_cell=("regret", lambda r: int((r < 1e-12).sum())),
                cells=("regret", "size"),
            )
            .assign(n_range=label)
        )
        frames.append(summary)
    return pd.concat(frames).reset_index().round(4)


def recall_by_edge_strength(data: pd.DataFrame) -> pd.DataFrame:
    config = stage7b.load_stage7b_config(CONFIG)
    cells = {(c.structure, c.p, c.n): c for c in stage7b.cells_for(config)}
    subset = data[data.method.isin(STRENGTH_METHODS)]
    strengths: dict[tuple[str, int, int], np.ndarray] = {}
    records = []
    for row in subset.itertuples():
        key = (row.structure, row.p, row.replicate)
        if key not in strengths:
            cell = cells[(row.structure, row.p, row.n)]
            rng = np.random.default_rng(stage7b.truth_seed(config, cell, row.replicate))
            truth = make_truth(row.structure, row.p, rng)
            strengths[key] = np.abs(truth.partial_correlations[np.triu_indices(row.p, 1)])
        weight = strengths[key]
        estimated = decode_edges(row.edge_bits, row.p)
        for low, high, label in STRENGTH_BINS:
            mask = (weight > 0) & (weight >= low) & (weight < high)
            records.append((row.method, row.n, label, int(estimated[mask].sum()), int(mask.sum())))
    table = pd.DataFrame(records, columns=["method", "n", "strength", "hits", "true_edges"])
    table = table.groupby(["strength", "method", "n"], as_index=False)[["hits", "true_edges"]].sum()
    table["recall"] = (table.hits / table.true_edges).round(4)
    return table


def main() -> None:
    data = load_validation()
    for name, frame in [
        ("operating_points.csv", operating_points(data)),
        ("fixed_setting_regret.csv", fixed_setting_regret(data)),
        ("recall_by_edge_strength.csv", recall_by_edge_strength(data)),
    ]:
        frame.to_csv(HERE / name, index=False)
        print(f"== {name}\n{frame.to_string(index=False)}\n")


if __name__ == "__main__":
    main()
