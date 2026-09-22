# Archived Stage 7a Evidence (scalable GOPC engine)

Raw per-replicate evidence backing `docs/decision_log.md`'s D-069, kept
as permanent tracked files (same convention as
`evidence/stage5_benchmarks/`).

| Directory | Decision | Source |
|---|---|---|
| `stage7a_engine` | D-069 (2026-09-22) | Local run (Windows, 20 CPUs, Python 3.11.9), full configuration `configs/stage7a_engine.yaml`, 11.5 minutes. The charter allowed a local run under two hours; see its pre-freeze resolutions. The run started at commit `131ec7f` (the frozen charter). `metadata.json`'s `git_commit` (`86f043d`) is HEAD at the time the file was *written*, after two commits that only added Stage 7b files (`git diff --stat 131ec7f 86f043d`), so the code that produced this evidence is `131ec7f`'s. `charter_sha256` matches the frozen charter. |

`raw_metrics.csv.gz` decompresses (`gzip -dk`) to `raw_metrics.csv`,
100,360 data rows (equal to `expected_row_count`). Checksums:

| File | SHA-256 |
|---|---|
| `raw_metrics.csv.gz` | `f4b2ff8882f2cf21377abc2c7c84bf10dce0e66cf9ceef81616dd8b7cf28964d` |
| `raw_metrics.csv` | `93a686f2edf359e2c884bf2226651161650335fec8854bfc328ea8a283af0497` |
