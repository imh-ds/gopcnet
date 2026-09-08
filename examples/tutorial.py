# %% [markdown]
# # gopcnet tutorial: a symptom network on messy, realistic data
#
# This walks through `gopcnet`'s public API end to end on a *simulated*
# comorbidity-style symptom network -- eight depression/anxiety symptoms,
# loosely modeled on the kind of data a real self-report study would
# produce. Unlike this package's own unit tests (which mostly use clean
# multivariate-normal chains so the math is easy to hand-verify), the
# data here is deliberately messier:
#
# - one symptom is right-skewed (a power transform, not re-standardized)
# - one is coarse, Likert-style ordinal (rounded to 5 levels)
# - one has a handful of injected outliers (measurement glitches)
# - one is mostly noise, weakly related to anything else
# - two symptoms ("bridge" symptoms) are conventionally categorized
#   under one diagnostic label but empirically correlate with both
#   symptom clusters -- exactly the situation bridge centrality
#   (the last analysis step below) is built to surface.
#
# This file is written in "percent" cell format (`# %%` markers) -- it
# runs top to bottom as a plain script (figures are saved to
# `examples/tutorial_output/`, not shown interactively), and each `# %%`
# marker is also where a matching Jupyter notebook (`tutorial.ipynb`,
# generated from this file) splits into its own cell.
#
# This is a worked example, not part of the installed `gopcnet` package
# -- the plotting helpers defined below are demonstration code, not a
# `gopcnet` API.

# %%
from __future__ import annotations

import os
import warnings
from functools import partial

import matplotlib

try:
    get_ipython()  # type: ignore[name-defined]  # defined only inside a Jupyter/IPython kernel
    _running_in_notebook = True
except NameError:
    _running_in_notebook = False

if not _running_in_notebook:
    matplotlib.use("Agg")  # headless script: save figures to disk instead of opening windows

import matplotlib.pyplot as plt
import numpy as np

import gopcnet

try:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _base_dir = os.getcwd()  # __file__ isn't defined when run as a notebook cell
OUTPUT_DIR = os.path.join(_base_dir, "tutorial_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def savefig(fig: plt.Figure, name: str) -> None:
    """Save to disk (so the plain script produces output files too) and
    explicitly `plt.show()` -- a no-op under the headless Agg backend
    used when running as a script, but the reliable, backend-agnostic
    way to trigger inline display when this cell runs inside a Jupyter
    notebook (rather than depending on IPython's own post-cell-execution
    auto-display, which isn't guaranteed the same way across every
    Jupyter setup)."""
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    with warnings.catch_warnings():
        # Expected, not a bug: the headless Agg backend can't actually
        # display a window, so plt.show() is a documented no-op there.
        warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive")
        plt.show()
    print(f"  saved {path}")


# %% [markdown]
# ## 1. Simulate messy symptom data
#
# Two correlated latent severity factors (depression, anxiety) drive
# eight observed symptoms. `fatigue` and `insomnia` load on *both*
# factors -- in real diagnostic manuals these are conventionally
# counted as depression criteria, but they empirically relate to
# anxiety too, which is exactly what makes them interesting "bridge"
# symptoms later on. Nothing about this cross-loading is given to
# `fit_gopc` -- it has to discover the structure from the (messy) data
# alone, the same as it would with a real dataset.

# %%
LABELS = [
    "sad_mood",
    "anhedonia",
    "fatigue",
    "worry",
    "tension",
    "restlessness",
    "insomnia",
    "appetite_change",
]

# DSM-style category each symptom is conventionally assigned to, despite
# fatigue/insomnia's real cross-loading onto the anxiety factor -- used
# later for bridge centrality, not by fit_gopc itself.
COMMUNITIES = np.array(
    ["depression", "depression", "depression", "anxiety", "anxiety", "anxiety", "depression", "depression"]
)


def simulate_messy_symptom_data(
    n: int,
    rng: np.random.Generator,
    *,
    anxiety_depression_correlation: float = 0.5,
    comorbid_bridge_boost: float = 0.0,
) -> np.ndarray:
    """Simulate `n` respondents' worth of 8 symptom ratings.

    `anxiety_depression_correlation` controls how strongly the two
    latent severity factors co-occur (comorbidity level).
    `comorbid_bridge_boost` additionally strengthens `fatigue`'s and
    `insomnia`'s own loading onto the anxiety factor -- used later to
    simulate a more severely comorbid second group for the network
    comparison test.
    """
    r = anxiety_depression_correlation
    factors = rng.multivariate_normal(mean=[0.0, 0.0], cov=[[1.0, r], [r, 1.0]], size=n)
    depression_factor, anxiety_factor = factors[:, 0], factors[:, 1]

    def signal_plus_noise(dep_loading: float, anx_loading: float, noise_scale: float = 1.0) -> np.ndarray:
        signal = dep_loading * depression_factor + anx_loading * anxiety_factor
        residual_variance = max(1e-6, 1.0 - dep_loading**2 - anx_loading**2)
        noise = noise_scale * np.sqrt(residual_variance) * rng.normal(size=n)
        return signal + noise

    sad_mood = signal_plus_noise(0.70, 0.00)

    # Right-skewed: a power transform applied to an otherwise normal
    # signal, left unstandardized on purpose -- real self-report items
    # are rarely symmetric.
    anhedonia_raw = signal_plus_noise(0.65, 0.00)
    anhedonia = np.sign(anhedonia_raw) * np.abs(anhedonia_raw) ** 1.6

    fatigue = signal_plus_noise(0.50, 0.30 + comorbid_bridge_boost)

    worry = signal_plus_noise(0.00, 0.70)

    # Coarse, Likert-style ordinal: rounded to 5 levels (0-4), the kind
    # of granularity a real self-report scale would have.
    tension_raw = signal_plus_noise(0.00, 0.60)
    tension_unit = (tension_raw - tension_raw.min()) / np.ptp(tension_raw)
    tension = np.round(tension_unit * 4.0)

    restlessness = signal_plus_noise(0.00, 0.55)
    # A handful of injected outliers -- e.g. a respondent mis-clicking
    # a 100-point slider instead of a 5-point one.
    n_outliers = max(1, n // 100)
    outlier_rows = rng.choice(n, size=n_outliers, replace=False)
    restlessness[outlier_rows] += rng.normal(loc=6.0, scale=1.0, size=n_outliers) * rng.choice(
        [-1.0, 1.0], size=n_outliers
    )

    insomnia = signal_plus_noise(0.40, 0.40 + comorbid_bridge_boost)

    # Near-isolated: mostly its own noise, only weakly tied to anything.
    appetite_change = signal_plus_noise(0.15, 0.00, noise_scale=1.3)

    return np.column_stack(
        [sad_mood, anhedonia, fatigue, worry, tension, restlessness, insomnia, appetite_change]
    )


rng = np.random.default_rng(20260907)
data = simulate_messy_symptom_data(n=600, rng=rng)
print(f"Simulated data: {data.shape[0]} respondents x {data.shape[1]} symptoms")
print("First 5 rows:")
print(np.round(data[:5], 2))

# %% [markdown]
# ## 2. A network-plotting helper
#
# `gopcnet` has no plotting of its own (no `networkx`/`igraph`
# dependency -- see `docs/decision_log.md`'s D-063 for the same
# reasoning applied to community detection). This is plain
# `matplotlib`: nodes placed evenly around a circle, edges colored by
# sign and scaled in width by `|weight|`.

# %%
def plot_network(
    weights: np.ndarray,
    labels: list[str],
    *,
    communities: np.ndarray | None = None,
    highlight: set[str] | None = None,
    title: str = "",
) -> plt.Figure:
    p = len(labels)
    angles = np.linspace(0.0, 2.0 * np.pi, p, endpoint=False)
    positions = np.column_stack([np.cos(angles), np.sin(angles)])

    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    max_weight = np.max(np.abs(weights)) if np.any(weights) else 1.0

    for i in range(p):
        for j in range(i + 1, p):
            weight = weights[i, j]
            if weight == 0.0:
                continue
            color = "#2b6cb0" if weight > 0 else "#c53030"
            ax.plot(
                [positions[i, 0], positions[j, 0]],
                [positions[i, 1], positions[j, 1]],
                color=color,
                linewidth=0.75 + 4.0 * abs(weight) / max_weight,
                alpha=0.75,
                zorder=1,
            )

    if communities is not None:
        unique_communities = sorted(set(communities.tolist()))
        cmap = plt.get_cmap("Set2")
        color_by_community = {c: cmap(k % 8) for k, c in enumerate(unique_communities)}
        node_colors = [color_by_community[c] for c in communities]
    else:
        node_colors = "#4a5568"

    edge_colors = ["gold" if (highlight and label in highlight) else "black" for label in labels]
    edge_widths = [3.0 if (highlight and label in highlight) else 1.0 for label in labels]
    ax.scatter(
        positions[:, 0], positions[:, 1], s=1400, c=node_colors,
        edgecolors=edge_colors, linewidths=edge_widths, zorder=2,
    )
    for (x, y), label in zip(positions, labels):
        ax.text(x * 1.35, y * 1.35, label, ha="center", va="center", fontsize=9)

    ax.set_xlim(-1.8, 1.8)
    ax.set_ylim(-1.8, 1.8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)
    return fig


# %% [markdown]
# ## 3. Fit the network
#
# `fit_gopc` is the recommended default (growing-order GOPC). Nothing
# here is told the true generative structure -- the screening and
# pruning thresholds are the only inputs.

# %%
result = gopcnet.fit_gopc(data, screening_alpha=0.05, dpi_alpha=0.05)
n_edges = int(np.triu(result.adjacency, k=1).sum())
print(f"GOPC found {n_edges} edges out of {len(LABELS) * (len(LABELS) - 1) // 2} possible")
for i, row_label in enumerate(LABELS):
    connections = [LABELS[j] for j, present in enumerate(result.adjacency[i]) if present]
    print(f"  {row_label}: {connections}")

fig = plot_network(result.weights, LABELS, communities=COMMUNITIES, title="GOPC network")
savefig(fig, "01_network.png")

# %% [markdown]
# ## 4. Compare against the two comparator methods
#
# `fit_ebicglasso` (graphical lasso, EBIC-selected penalty) and
# `fit_pc_skeleton` (the PC algorithm's skeleton phase) are included in
# `gopcnet` for exactly this: benchmarking GOPC's structure against
# established alternatives on the same data.

# %%
ebic_result = gopcnet.fit_ebicglasso(data)
pc_result = gopcnet.fit_pc_skeleton(data, alpha=0.01)

print(f"GOPC edges:        {n_edges}")
print(f"EBICglasso edges:  {int(np.triu(ebic_result.adjacency, k=1).sum())}")
print(f"PC skeleton edges: {int(np.triu(pc_result.adjacency, k=1).sum())}")

for method_result, method_name, filename in (
    (result, "GOPC", "02a_network_gopc.png"),
    (ebic_result, "EBICglasso", "02b_network_ebicglasso.png"),
    (pc_result, "PC skeleton", "02c_network_pc.png"),
):
    weights = getattr(method_result, "weights", method_result.adjacency.astype(float))
    fig = plot_network(weights, LABELS, communities=COMMUNITIES, title=method_name)
    savefig(fig, filename)

# %% [markdown]
# ## 5. Bootstrap edge stability and the CS-coefficient
#
# How much would these edges change under a different sample of the
# same size? `bootstrap_edge_stability` resamples the data (with
# replacement) and refits repeatedly; `case_drop_bootstrap` +
# `cs_coefficient` answer a related but different question -- how much
# of the sample could be dropped before a centrality ordering stops
# resembling the full-sample one.

# %%
fit = partial(gopcnet.fit_gopc, screening_alpha=0.05, dpi_alpha=0.05)

stability = gopcnet.bootstrap_edge_stability(data, fit, bootstraps=150, rng=np.random.default_rng(1))
print(f"Bootstrap edge stability: {stability.successful_bootstraps} succeeded, "
      f"{stability.failed_bootstraps} failed")

fig, ax = plt.subplots(figsize=(7, 5))
upper = np.triu_indices(len(LABELS), k=1)
inclusion_values = stability.inclusion_probability[upper]
pair_labels = [f"{LABELS[i]}-{LABELS[j]}" for i, j in zip(*upper)]
order = np.argsort(inclusion_values)[::-1]
ax.barh(
    [pair_labels[k] for k in order][:15],
    [inclusion_values[k] for k in order][:15],
    color="#2b6cb0",
)
ax.set_xlabel("bootstrap inclusion probability")
ax.set_title("Top 15 edges by bootstrap inclusion probability")
ax.invert_yaxis()
fig.tight_layout()
savefig(fig, "03_edge_stability.png")

case_drop = gopcnet.case_drop_bootstrap(
    data, fit, lambda r: gopcnet.strength(r.weights),
    bootstraps_per_proportion=80, rng=np.random.default_rng(2),
)
cs = gopcnet.cs_coefficient(case_drop)
print(f"CS-coefficient (strength): {cs.cs_coefficient:.2f}")
print("Pass rate by proportion of sample retained:")
for proportion, pass_rate in sorted(cs.pass_rate_by_proportion_retained.items(), reverse=True):
    print(f"  {proportion:.1f} retained -> {pass_rate:.2f} pass rate")

# %% [markdown]
# ## 6. Centrality
#
# `compute_centrality` bundles all four standard measures. `fatigue`
# and `insomnia` -- the two symptoms simulated to load on *both*
# latent factors -- are worth watching here.

# %%
centrality = gopcnet.compute_centrality(result.weights)
for i, label in enumerate(LABELS):
    print(
        f"  {label:16s} strength={centrality.strength[i]:.2f}  "
        f"EI={centrality.expected_influence[i]:.2f}  "
        f"closeness={centrality.closeness[i]:.3f}  "
        f"betweenness={centrality.betweenness[i]:.2f}"
    )

fig, axes = plt.subplots(2, 2, figsize=(11, 8))
measures = [
    ("strength", centrality.strength),
    ("expected_influence", centrality.expected_influence),
    ("closeness", centrality.closeness),
    ("betweenness", centrality.betweenness),
]
for ax, (name, values) in zip(axes.flat, measures):
    order = np.argsort(values)
    ax.barh([LABELS[i] for i in order], [values[i] for i in order], color="#4a5568")
    ax.set_title(name)
fig.tight_layout()
savefig(fig, "04_centrality.png")

# %% [markdown]
# ## 7. Difference test: is `worry` really more central than `appetite_change`?
#
# `appetite_change` was simulated to be near-isolated; `worry` loads
# strongly on the anxiety factor. `bootstrap_replicates` +
# `difference_test` gives a bootstrap confidence interval on the
# difference in their strength, rather than just comparing the two
# point estimates.

# %%
replicates = gopcnet.bootstrap_replicates(
    data, fit, lambda r: gopcnet.strength(r.weights), bootstraps=150, rng=np.random.default_rng(3)
)
worry_idx, appetite_idx = LABELS.index("worry"), LABELS.index("appetite_change")
diff = gopcnet.difference_test(replicates, index_a=worry_idx, index_b=appetite_idx)
print(
    f"strength[worry] - strength[appetite_change] = {diff.difference:.2f}, "
    f"95% CI [{diff.ci_low:.2f}, {diff.ci_high:.2f}], significant={diff.significant}"
)

# %% [markdown]
# ## 8. Goodness of fit
#
# `fit_gaussian_graphical_model` gives AIC/BIC/EBIC for the discovered
# structure; `fit_indices` adds the SEM tradition's own RMSEA/CFI/TLI/
# SRMR. `train_test_fit_indices` then checks whether that fit holds up
# out of sample -- since the structure was *searched for* on this exact
# data, an in-sample-only fit check is optimistic (see
# `docs/decision_log.md`'s D-060).

# %%
ggm_fit = gopcnet.fit_gaussian_graphical_model(data, result.adjacency)
indices = gopcnet.fit_indices(data, result.adjacency)
print(f"log-likelihood={ggm_fit.log_likelihood:.2f}  AIC={ggm_fit.aic:.2f}  "
      f"BIC={ggm_fit.bic:.2f}  EBIC={ggm_fit.ebic:.2f}")
print(f"chi-square={indices.chi_square:.2f} (df={indices.df}, p={indices.p_value:.3f})")
print(f"RMSEA={indices.rmsea:.4f}  CFI={indices.cfi:.4f}  TLI={indices.tli:.4f}  SRMR={indices.srmr:.4f}")

train_test = gopcnet.train_test_fit_indices(data, fit, test_proportion=0.5, rng=np.random.default_rng(4))
print(f"\nIn-sample RMSEA:     {train_test.in_sample.rmsea:.4f}")
print(f"Out-of-sample RMSEA: {train_test.out_of_sample.rmsea:.4f}")
print("(the out-of-sample number is the honest one -- see D-060)")

# %% [markdown]
# ## 9. Whole-network descriptives

# %%
summary = gopcnet.compute_global_metrics(result.adjacency, result.weights)
print(f"density={summary.density:.2f}  global_strength={summary.global_strength:.2f}  "
      f"clustering={summary.clustering_coefficient:.2f}  "
      f"avg_shortest_path={summary.average_shortest_path_length:.2f}")

# %% [markdown]
# ## 10. Bridge centrality
#
# Using the DSM-style category labels assigned above (which do *not*
# reflect `fatigue`/`insomnia`'s real cross-loading), bridge centrality
# should flag them as the symptoms doing the most work connecting the
# two labeled communities -- exactly the situation this measure exists
# to surface (Jones, Ma, & McNally, 2021).

# %%
bridges = gopcnet.compute_bridge_centrality(result.weights, COMMUNITIES)
order = np.argsort(bridges.strength)[::-1]
print("Bridge strength (highest first):")
for i in order:
    print(f"  {LABELS[i]:16s} ({COMMUNITIES[i]:>10s})  bridge_strength={bridges.strength[i]:.2f}")

top_two_bridges = {LABELS[i] for i in order[:2]}
fig = plot_network(
    result.weights, LABELS, communities=COMMUNITIES, highlight=top_two_bridges,
    title="Network with top-2 bridge symptoms highlighted",
)
savefig(fig, "05_bridge_network.png")

# %% [markdown]
# ## 11. Network comparison test: a more comorbid second group
#
# Simulate a second, independent sample from a more severely comorbid
# population (higher depression-anxiety factor correlation, and a
# stronger cross-loading for the two bridge symptoms specifically), and
# test whether `network_comparison_test` can tell the two networks
# apart.

# %%
rng_b = np.random.default_rng(20260908)
data_comorbid = simulate_messy_symptom_data(
    n=450, rng=rng_b, anxiety_depression_correlation=0.85, comorbid_bridge_boost=0.25
)

nct_result = gopcnet.network_comparison_test(
    data, data_comorbid, fit, permutations=250, rng=np.random.default_rng(5)
)
print(
    f"Global strength difference: {nct_result.observed_global_strength_difference:.2f} "
    f"(p={nct_result.global_strength_p_value:.3f})"
)
print(
    f"Max edge weight difference: {nct_result.observed_max_edge_weight_difference:.2f} "
    f"(p={nct_result.max_edge_weight_difference_p_value:.3f})"
)

# %% [markdown]
# ## 12. A "safe" network from bootstrap evidence
#
# As a final step, `threshold_by_inclusion_probability` turns the
# bootstrap edge-stability result from step 5 into an adjacency matrix
# containing only the edges that survived a chosen inclusion threshold
# -- a more conservative structure to report than the single
# point-estimate `fit_gopc` result alone.

# %%
safe_adjacency = gopcnet.threshold_by_inclusion_probability(stability.inclusion_probability, threshold=0.9)
print("Edges retained at >=90% bootstrap inclusion:")
for i, row in enumerate(safe_adjacency):
    connections = [LABELS[j] for j, present in enumerate(row) if present]
    if connections:
        print(f"  {LABELS[i]}: {connections}")

print(f"\nAll figures saved to {OUTPUT_DIR}")
