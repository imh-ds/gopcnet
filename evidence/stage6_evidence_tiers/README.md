# Archived Stage 6 Evidence (edge-evidence tiers)

Raw per-replicate evidence backing `docs/decision_log.md`'s D-066,
archived here as permanent tracked files. GitHub Actions deletes shard
artifacts after 14 days and aggregated artifacts after 90, so
committing the evidence keeps it regardless of that clock. The
convention is the same as `evidence/stage5_benchmarks/`.

| Directory | Decision(s) | Source |
|---|---|---|
| `stage6a_bridge_validation` | D-066 (2026-09-22) | GitHub Actions run [35703700288](https://github.com/imh-ds/gopcnet/actions/runs/35703700288), commit `ada49f1`, 25 shards plus aggregate, all succeeded. The aggregate artifact (`aggregated-benchmark`) contains `raw_metrics.csv`, `report.json`, `stage6a_report.md`, `full_grid_validation.csv` and the figure, but no `resolved_config.yaml` or `metadata.json`. Those two came from one shard artifact (`shard-no_bridge_negative_control-500`); every shard writes the same resolved configuration. That shard's `metadata.json` is kept as `shard_metadata_example.json`, and its `charter_sha256` (`16eb6aef…f180`) equals `sha256sum docs/stage6a_charter.md` at archive time. |

## Reassembling `raw_metrics.csv`

The raw file is 694 MB, and 117 MB gzip-compressed, which exceeds
GitHub's 100 MB per-file limit. It is therefore stored as two byte-split
parts of the gzip stream. Reassemble with:

```bash
cat raw_metrics.csv.gz.part00 raw_metrics.csv.gz.part01 > raw_metrics.csv.gz
gzip -dk raw_metrics.csv.gz
```

Verify:

| File | SHA-256 |
|---|---|
| `raw_metrics.csv.gz` (reassembled) | `6a23950c16641d6dc10e5947e3997f79702634264ae7c81846059a53284589be` |
| `raw_metrics.csv` | `2d0c7fe57b1e5a47a915fc1f7b4647df95546db65d47624e7ae745733b6fa3cf` |

`raw_metrics.csv` has 5,430,000 data rows, equal to
`gopcnet.experiments.stage6a.expected_row_count` for
`configs/stage6a_bridge_validation.yaml`.
