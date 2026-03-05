# Investigation Findings: Local vs Service Metadata

This document summarizes observed behavior differences while running `MetadataProbeFlow` against:
- local metadata (`--metadata=local`)
- metadata service (`--metadata=service`, dev stack)

All runs used the same flow code in `metadata_probe_flow.py`.

## Runs Executed

### Baseline success + retry probe
- Local run: `MetadataProbeFlow/1772612468704135`
  - Snapshots: `local_snapshots_success.json`
- Service run: `MetadataProbeFlow/1`
  - Snapshots: `service_snapshots_success.json`

### Failure scenario (`--fail-in-step post_join`)
- Local run: `MetadataProbeFlow/1772615157479396`
  - Snapshots: `local_snapshots_fail_post_join.json`
- Service run: `MetadataProbeFlow/2`
  - Snapshots: `service_snapshots_fail_post_join.json`

### Mid-run termination experiment
- Local run killed early: `MetadataProbeFlow/1772615394319701`
  - Snapshots: `local_snapshots_midkill.json`
- Service run kill attempt: `MetadataProbeFlow/3`
  - Snapshots: `service_snapshots_midkill.json`

## Key Observations

1. **Run-level completion semantics matched in tested scenarios**
   - Successful baseline run:
     - both backends eventually reported `finished=True`, `successful=True`, and `end_task_exists=True`.
   - Post-join failure scenario:
     - both backends reported `finished=False`, `successful=False`, and `end_task_exists=False`.

2. **Polling cadence differed significantly**
   - Requested snapshot interval was 2s in both cases.
   - Actual observed cadence from saved snapshots:
     - local success avg interval: ~1.92s
     - service success avg interval: ~12.02s
     - local fail avg interval: ~1.95s
     - service fail avg interval: ~8.05s
   - This indicates much higher query latency (or effective poll delay) when reading from service in this dev environment.

3. **Identifier shape differences are expected**
   - Local run IDs are timestamp-like (`177261...`), service run IDs are small integers (`1`, `2`, `3`).
   - Task IDs and step/task pathspecs differ by run and backend context, so direct task-path equality in cross-backend comparisons is not a reliable signal by itself.

4. **Retry behavior was visible in both backends**
   - Intentional first-attempt failure in branch 0 retried and completed.
   - Both local and service runs completed baseline scenario successfully after retry.

5. **Mid-run termination behavior needs deeper follow-up**
   - Killing the top-level local CLI process produced an incomplete run view (`finished=False`, `successful=False`) for that run.
   - Killing the dev-shell wrapper process in service mode did **not** stop the run; the run completed successfully.
   - This suggests process-tree/lifecycle handling differences in how runs survive caller termination, but this test should be repeated with stricter worker/process-level kill methods for both backends.

## Generated Comparison Reports

- `snapshot_comparison_success.md`
- `snapshot_comparison_fail_post_join.md`

These reports are useful for quick checks but currently compare task pathspecs directly. Since IDs differ between runs/backends, treat task-level DIFF lines as hints, not definitive correctness failures.

## Severity Assessment (Current)

- **Potentially meaningful difference**: service polling latency in this setup appears much higher than local.
- **No severe semantic mismatch observed yet** for run final state in the tested success/failure scenarios.
- **Open question**: robust run interruption semantics parity (needs refined kill experiment).

## Recommended Next Discussion with Maintainer

1. Should parity checks prioritize only user-facing semantics (`Run.finished/successful/finished_at`, step/task terminal states), not raw ID/path matching?
2. Is high service-side client polling latency expected in local dev stack, or indicative of inefficiency/regression?
3. What is the expected behavior when launcher process is terminated mid-run for local vs service backends?
