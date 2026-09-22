# Stage 5i report: PC significance-level sweep

Charter: `docs/stage5i_charter.md` (FROZEN before results). All comparisons below use validation replicates only.

## G1 / G2 (pipeline integrity)

- **G1**: FAILED — rows compared 38000, identical fraction 0.99087, worst cell-mean difference 0.01050
  - post-hoc, not predeclared — overlap|1500: identical fraction 0.8265; n_estimated_edges diff +0.0105 (z=0.66); precision diff -0.0010 (z=-0.69)
  - post-hoc, not predeclared — overlap|1750: identical fraction 0.8385; n_estimated_edges diff -0.0085 (z=-0.50); precision diff +0.0008 (z=0.52)
  - excluded per charter amendment (archive anomaly, reported not gated): overlap|1750, 2000 rows, identical fraction 0.8385
- **G2**: FAILED — rows compared 40000, identical fraction 0.99028, worst cell-mean difference 0.02050
  - post-hoc, not predeclared — overlap|1500: identical fraction 0.8055; n_estimated_edges diff +0.0205 (z=1.03); precision diff -0.0018 (z=-1.07)

**Gate outcome and post-hoc diagnosis (added after the full run; not part of the frozen charter).** Both gates FAIL as the charter defined them and are reported as failed. Every failing cell is `overlap`; all other cells reproduce the archives exactly. The most likely cause: the `overlap` sampler draws with `numpy.random.Generator.multivariate_normal`, which factors the covariance by SVD, and that covariance has a repeated singular value (0.8, twice), so the SVD's rotation within that 2-D subspace is not pinned down and can depend on the machine's floating-point behavior. Every rotation is a valid factorization of the same covariance, so draws follow the same distribution but a given seed can yield different data. Supporting evidence: a local check that swaps the factorization (`svd` vs `eigh`) on identical seeds changes PC's edge count in 8% (N=1000) to 16% (N=1500) of replicates, the same order as the 17-19% seen here. NOT directly demonstrated: that the CI machines actually differ in this way. The per-cell unpaired z-scores above show the differing cells agree within sampling noise. This does not affect any comparison inside this run, where every method sees the same draw. `triangle_balanced` shares the repeated-singular-value property but its edge counts cannot reveal it.

## Single-alpha selection (development replicates)

| N | primary (50/50) | equal per shape | composed only | triangles only |
|---|---|---|---|---|
| 750 | 0.005 | 0.01 | 0.001 | 0.2 |
| 1000 | 0.005 | 0.01 | 0.001 | 0.2 |
| 1500 | 0.005 | 0.005 | 0.001 | 0.2 |
| 1750 | 0.005 | 0.005 | 0.001 | 0.2 |

Per-shape oracle alpha (upper bound on PC tunability, NOT a deployable method):

| N | chain_fork_hub | overlap | triangle_balanced | triangle_moderate | triangle_strong |
|---|---|---|---|---|---|
| 750 | 0.001 | 0.001 | 0.001 | 0.2 | 0.2 |
| 1000 | 0.001 | 0.001 | 0.001 | 0.2 | 0.2 |
| 1500 | 0.001 | 0.001 | 0.001 | 0.1 | 0.2 |
| 1750 | 0.001 | 0.001 | 0.001 | 0.025 | 0.2 |

## Q1 — Is the weak-edge recall deficit an alpha artifact?

**triangle_moderate** — 4 of 4 N within tolerance: *recall deficit was the significance level (restate the manuscript's recall claim)*

| N | PC@matched | GOPC | paired diff [95% CI] | PC@.01 | pred PC@.01 | pred matched | gap |
|---|---|---|---|---|---|---|---|
| 750 | 0.988 | 0.988 | +0.0000 [+0.0000, +0.0000] | 0.922 | 0.921 | 0.989 | -0.001 |
| 1000 | 0.995 | 0.995 | +0.0000 [+0.0000, +0.0000] | 0.965 | 0.964 | 0.996 | -0.001 |
| 1500 | 0.999 | 0.999 | +0.0000 [+0.0000, +0.0000] | 0.996 | 0.994 | 1.000 | -0.000 |
| 1750 | 1.000 | 1.000 | +0.0000 [+0.0000, +0.0000] | 0.998 | 0.998 | 1.000 | +0.000 |

**triangle_strong** — 4 of 4 N within tolerance: *recall deficit was the significance level (restate the manuscript's recall claim)*

| N | PC@matched | GOPC | paired diff [95% CI] | PC@.01 | pred PC@.01 | pred matched | gap |
|---|---|---|---|---|---|---|---|
| 750 | 0.930 | 0.930 | +0.0000 [+0.0000, +0.0000] | 0.793 | 0.783 | 0.924 | +0.007 |
| 1000 | 0.952 | 0.952 | +0.0000 [+0.0000, +0.0000] | 0.831 | 0.827 | 0.949 | +0.004 |
| 1500 | 0.977 | 0.977 | +0.0000 [+0.0000, +0.0000] | 0.898 | 0.900 | 0.978 | -0.001 |
| 1750 | 0.986 | 0.986 | +0.0000 [+0.0000, +0.0000] | 0.923 | 0.927 | 0.985 | +0.000 |

## Q2 — Is PC's precision edge an alpha artifact?

**chain_fork_hub** — PC below GOPC by >.01 at 4 of 4 N; holds within .01 at 0 of 4: *PC's precision edge was the strictness of alpha = .01 (GOPC's decoupled design reaches precision PC cannot at loose alpha)*

| N | PC@matched | GOPC | PC@.01 | paired diff [95% CI] |
|---|---|---|---|---|
| 750 | 0.469 | 0.930 | 0.950 | -0.4611 [-0.4676, -0.4544] |
| 1000 | 0.499 | 0.935 | 0.949 | -0.4364 [-0.4435, -0.4292] |
| 1500 | 0.561 | 0.946 | 0.945 | -0.3852 [-0.3927, -0.3773] |
| 1750 | 0.575 | 0.946 | 0.949 | -0.3719 [-0.3794, -0.3649] |

**overlap** — PC below GOPC by >.01 at 4 of 4 N; holds within .01 at 0 of 4: *PC's precision edge was the strictness of alpha = .01 (GOPC's decoupled design reaches precision PC cannot at loose alpha)*

| N | PC@matched | GOPC | PC@.01 | paired diff [95% CI] |
|---|---|---|---|---|
| 750 | 0.640 | 0.952 | 0.975 | -0.3121 [-0.3178, -0.3067] |
| 1000 | 0.666 | 0.955 | 0.973 | -0.2891 [-0.2948, -0.2830] |
| 1500 | 0.713 | 0.960 | 0.974 | -0.2463 [-0.2524, -0.2403] |
| 1750 | 0.733 | 0.967 | 0.974 | -0.2347 [-0.2402, -0.2290] |

## Q3 — Does one alpha suffice?

- **primary**: PC comparable-or-better in 14 of 20 cells; N with all five shapes comparable: none
- **sensitivity_equal_per_shape**: PC comparable-or-better in 14 of 20 cells; N with all five shapes comparable: none
- **sensitivity_per_group**: PC comparable-or-better in 20 of 20 cells; N with all five shapes comparable: [750, 1000, 1500, 1750]

## Q4 — Mechanism check (matched GOPC capped at conditioning order 2; PC uncapped)

**alpha_0.01**

| shape | GOPC-vs-PC mean sym. diff | noise floor | verdict |
|---|---|---|---|
| chain_fork_hub | 0.019 | 0.100 | effectively the same search at matched alpha (up to order-2 tests) |
| overlap | 0.035 | 0.084 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_balanced | 0.000 | 0.000 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_moderate | 0.000 | 0.011 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_strong | 0.000 | 0.030 | effectively the same search at matched alpha (up to order-2 tests) |

**alpha_0.1**

| shape | GOPC-vs-PC mean sym. diff | noise floor | verdict |
|---|---|---|---|
| chain_fork_hub | 0.473 | 1.352 | effectively the same search at matched alpha (up to order-2 tests) |
| overlap | 0.526 | 1.131 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_balanced | 0.000 | 0.000 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_moderate | 0.000 | 0.003 | effectively the same search at matched alpha (up to order-2 tests) |
| triangle_strong | 0.000 | 0.020 | effectively the same search at matched alpha (up to order-2 tests) |

## Negative control (`triangle_balanced`)

F1 range across methods (alpha >= .005) by N: {750: 0.0, 1000: 0.0, 1500: 0.0, 1750: 0.0} — no separation, as expected.

Full validation grid: `full_grid_validation.csv`. Figure: `recall_precision_vs_alpha.png`.
