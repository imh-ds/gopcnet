# Archived Stage 7b Evidence (external validity)

Raw per-replicate evidence backing `docs/decision_log.md`'s D-070, kept
as permanent tracked files (same convention as
`evidence/stage5_benchmarks/`).

| Directory | Decision | Source |
|---|---|---|
| `stage7b_benchmark` | D-070 (2026-09-23) | GitHub Actions run [35787621191](https://github.com/imh-ds/gopcnet/actions/runs/35787621191) on branch `phase1/scalable-engine`, commit `53cfcda` (the frozen charter). 160 shards (16 cell tokens x 10 replicate blocks of 50) plus aggregate, all succeeded, 4 h 34 min. The aggregate artifact has no `resolved_config.yaml` or `metadata.json`, so those came from shard `shard-random_sparse-p10-0-49` (kept as `shard_metadata_example.json`). Its `charter_sha256` (`447cf737…c007`) equals the frozen charter's hash. |

`raw_metrics.csv.gz` decompresses (`gzip -dk`) to `raw_metrics.csv`,
252,200 data rows (equal to `expected_row_count`), all with
`status = ok`. Checksums:

| File | SHA-256 |
|---|---|
| `raw_metrics.csv.gz` | `674dbc1e641fb202ff829886e2a61a099908c433fd58c03c91cac3645b863659` |
| `raw_metrics.csv` | `d88ce9570ef77047a1507b190d3717c745a920c0eb2d37707a87c96fa5bcc836` |
