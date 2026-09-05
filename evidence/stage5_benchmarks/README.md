# Archived Stage 5 Benchmark Evidence

Raw per-replicate evidence backing `docs/decision_log.md`'s D-047
through D-052 entries, archived here as permanent tracked files
(GitHub Actions artifact storage expires shard-level data after 14
days and aggregated data after 90 -- committing this makes it
permanent regardless of that clock).

| Directory | Decision(s) | Source |
|---|---|---|
| `stage5a_comparator_benchmark` | D-047, D-048 | Ran locally, before the sharded GitHub Actions workflow existed -- no Actions run to point to; this local copy is the only surviving source. |
| `stage5b_noise_stress_test` | D-048 | GitHub Actions run `33534728141` (2026-09-01) |
| `stage5c_p_adjusted_alpha` | D-049 | GitHub Actions run `33551121806` (2026-09-01) |
| `stage5d_strength_sweep` | D-050 | GitHub Actions run `33567686017` (2026-09-01) |
| `stage5e_pc_skeleton` | D-051 (corrected) | GitHub Actions run `33589193320` (2026-09-02) |
| `stage5f_diagnostic` | D-052 | Local copy, contemporaneous with the above |

Each directory contains the same `raw_metrics.csv` / `report.json` /
`resolved_config.yaml` / `metadata.json` / `*_report.md` (plus figures
where generated) that the original mintnet repo's `stage5*.py` runners
and `stage5*_reporting.py` modules produced -- unmodified, copied
directly from the local worktree that fed the original decision-log
entries.

Not included: Stage 6a's growing-subset DPI architecture result
(D-053) -- scientifically relevant (tested using only the already-
validated Fisher-z partial-correlation primitive, no MI), but its code
(`growing_subset_dpi.py`) lives only on mintnet's `mi-native` branch,
not in the `v1-partial-correlation-baseline` tag this repo was seeded
from. Archiving the raw evidence without the code that produced it
would be an orphaned artifact -- pending a decision on whether to port
that code into this repo first.
