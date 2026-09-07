# Stage 5g Growing-Subset DPI vs. PC Skeleton Report

**Overall: PROCEED -- recall holds and at least PARTIAL closure observed on both diagnosed shapes.**

**Recall check: Recall holds within 0.02 of GOPC-original at every tested cell -- the growing-subset fix does not trade recall for precision.**

GOPC-original (D-047) and PC (D-051) numbers loaded from `evidence/stage5_benchmarks/` -- not re-run, computed on identically-seeded data.

## Per-shape closure verdict

| DGP shape | material | partial | none | gap cells (of 7) | Verdict |
|---|---|---|---|---|---|
| chain_fork_hub | 2 | 5 | 0 | 7 | PARTIAL closure at a majority of gap cells (5/7 partial, 2/7 material) |
| overlap | 7 | 0 | 0 | 7 | MATERIAL closure at a majority of gap cells (7/7) |
| triangle_balanced | 0 | 0 | 0 | 0 | no precision gap present at this shape (nothing to close) |
| triangle_moderate | 0 | 0 | 0 | 0 | no precision gap present at this shape (nothing to close) |
| triangle_strong | 0 | 0 | 0 | 0 | no precision gap present at this shape (nothing to close) |

## chain_fork_hub

| N | GOPC-original precision | PC precision | growing-subset precision | closure | original recall | growing-subset recall | recall OK |
|---|---|---|---|---|---|---|---|
| 400 | 0.9179 | 0.9452 | 0.9255 | 0.2785 | 1.0000 | 1.0000 | True |
| 500 | 0.9125 | 0.9498 | 0.9207 | 0.2200 | 1.0000 | 1.0000 | True |
| 600 | 0.9166 | 0.9468 | 0.9246 | 0.2651 | 1.0000 | 1.0000 | True |
| 750 | 0.9228 | 0.9503 | 0.9299 | 0.2577 | 1.0000 | 1.0000 | True |
| 1000 | 0.9267 | 0.9486 | 0.9349 | 0.3746 | 1.0000 | 1.0000 | True |
| 1500 | 0.9363 | 0.9450 | 0.9457 | 1.0862 | 1.0000 | 1.0000 | True |
| 1750 | 0.9391 | 0.9486 | 0.9465 | 0.7740 | 1.0000 | 1.0000 | True |

## overlap

| N | GOPC-original precision | PC precision | growing-subset precision | closure | original recall | growing-subset recall | recall OK |
|---|---|---|---|---|---|---|---|
| 400 | 0.8792 | 0.9755 | 0.9456 | 0.6893 | 1.0000 | 1.0000 | True |
| 500 | 0.8577 | 0.9720 | 0.9454 | 0.7670 | 1.0000 | 1.0000 | True |
| 600 | 0.8478 | 0.9776 | 0.9478 | 0.7702 | 1.0000 | 1.0000 | True |
| 750 | 0.8398 | 0.9747 | 0.9523 | 0.8344 | 1.0000 | 1.0000 | True |
| 1000 | 0.8611 | 0.9726 | 0.9551 | 0.8432 | 1.0000 | 1.0000 | True |
| 1500 | 0.9153 | 0.9756 | 0.9616 | 0.7678 | 1.0000 | 1.0000 | True |
| 1750 | 0.9265 | 0.9740 | 0.9672 | 0.8577 | 1.0000 | 1.0000 | True |

## triangle_balanced

| N | GOPC-original precision | PC precision | growing-subset precision | closure | original recall | growing-subset recall | recall OK |
|---|---|---|---|---|---|---|---|
| 400 | 1.0000 | 1.0000 | 1.0000 | None | 0.9997 | 0.9997 | True |
| 500 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |
| 600 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |
| 750 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |
| 1000 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |
| 1500 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |
| 1750 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |

## triangle_moderate

| N | GOPC-original precision | PC precision | growing-subset precision | closure | original recall | growing-subset recall | recall OK |
|---|---|---|---|---|---|---|---|
| 400 | 1.0000 | 1.0000 | 1.0000 | None | 0.9470 | 0.9470 | True |
| 500 | 1.0000 | 1.0000 | 1.0000 | None | 0.9697 | 0.9697 | True |
| 600 | 1.0000 | 1.0000 | 1.0000 | None | 0.9747 | 0.9747 | True |
| 750 | 1.0000 | 1.0000 | 1.0000 | None | 0.9883 | 0.9883 | True |
| 1000 | 1.0000 | 1.0000 | 1.0000 | None | 0.9950 | 0.9950 | True |
| 1500 | 1.0000 | 1.0000 | 1.0000 | None | 0.9993 | 0.9993 | True |
| 1750 | 1.0000 | 1.0000 | 1.0000 | None | 1.0000 | 1.0000 | True |

## triangle_strong

| N | GOPC-original precision | PC precision | growing-subset precision | closure | original recall | growing-subset recall | recall OK |
|---|---|---|---|---|---|---|---|
| 400 | 1.0000 | 1.0000 | 1.0000 | None | 0.8683 | 0.8683 | True |
| 500 | 1.0000 | 1.0000 | 1.0000 | None | 0.8880 | 0.8880 | True |
| 600 | 1.0000 | 1.0000 | 1.0000 | None | 0.9040 | 0.9040 | True |
| 750 | 1.0000 | 1.0000 | 1.0000 | None | 0.9303 | 0.9303 | True |
| 1000 | 1.0000 | 1.0000 | 1.0000 | None | 0.9523 | 0.9523 | True |
| 1500 | 1.0000 | 1.0000 | 1.0000 | None | 0.9770 | 0.9770 | True |
| 1750 | 1.0000 | 1.0000 | 1.0000 | None | 0.9857 | 0.9857 | True |

Closure = (growing_subset_precision - original_precision) / (pc_precision - original_precision), computed only where PC's precision exceeds GOPC-original's (a real diagnosed gap). See `docs/stage5g_charter.md`'s own selection-and-gate section for the frozen criteria.
