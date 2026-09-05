# Stage 5f Diagnostic Report -- Passthrough-Unconditioned False Edges (R6)

Tests whether MINT's DPI step's clique-shape scope (only conditions within validated 3/4/5-node candidate components) is a material source of MINT's own residual false positives on the two composed noisy networks. No algorithm change; pure post-hoc attribution of `compose_screen_then_prune`'s own unmodified output.

## Per-shape reading

| DGP shape | material | partial | minimal | Reading |
|---|---|---|---|---|
| chain_fork_hub | 0/7 | 7/7 | 0/7 | PARTIAL: passthrough-unconditioned edges are a non-trivial but non-majority contributor at a majority of tested N (0 material + 7 partial of 7) |
| overlap | 5/7 | 2/7 | 0/7 | MATERIAL: passthrough-unconditioned edges are a majority of MINT's own false positives at 5/7 tested N |

## chain_fork_hub

| N | DPI-conditioned true | DPI-conditioned false | passthrough true | passthrough false | passthrough share of false | errors |
|---|---|---|---|---|---|---|
| 400 | 11310 | 869 | 690 | 347 | 0.2854 | 0 |
| 500 | 11522 | 938 | 478 | 372 | 0.2840 | 0 |
| 600 | 11578 | 940 | 422 | 400 | 0.2985 | 0 |
| 750 | 11634 | 828 | 366 | 361 | 0.3036 | 0 |
| 1000 | 11602 | 775 | 398 | 394 | 0.3370 | 0 |
| 1500 | 11590 | 605 | 410 | 396 | 0.3956 | 0 |
| 1750 | 11682 | 611 | 318 | 321 | 0.3444 | 0 |

## overlap

| N | DPI-conditioned true | DPI-conditioned false | passthrough true | passthrough false | passthrough share of false | errors |
|---|---|---|---|---|---|---|
| 400 | 7872 | 690 | 12128 | 2291 | 0.7685 | 0 |
| 500 | 8554 | 692 | 11446 | 2965 | 0.8108 | 0 |
| 600 | 9238 | 726 | 10762 | 3365 | 0.8225 | 0 |
| 750 | 11046 | 776 | 8954 | 3397 | 0.8140 | 0 |
| 1000 | 14070 | 895 | 5930 | 2780 | 0.7565 | 0 |
| 1500 | 18316 | 1077 | 1684 | 1024 | 0.4874 | 0 |
| 1750 | 18784 | 1040 | 1216 | 876 | 0.4572 | 0 |

Descriptive attribution, not a validation gate or a fix -- see `docs/stage5f_charter.md`'s own decision structure and non-goals. See `raw_metrics.csv`, `report.json`, and `resolved_config.yaml` for complete evidence.
