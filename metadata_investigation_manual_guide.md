# Manual Investigation Guide: Local Metadata vs Metadata Service

This guide lets you manually run and inspect the issue about potential differences between:
- `--metadata=local`
- `--metadata=service`

using a reproducible flow and helper scripts, without full automation.

## Files Added

- `metadata_probe_flow.py`  
  Repro flow with:
  - foreach fanout
  - retry probe (first attempt failure on branch 0)
  - optional intentional failures
  - deliberate sleep windows for in-flight polling

- `collect_metadata_snapshots.py`  
  Polls Metaflow client state and saves structured snapshots to JSON.

- `compare_metadata_snapshots.py`  
  Compares local vs service final snapshots and prints a diff-style summary.

## Prerequisites

1. Metaflow installed in your environment.
2. Local dev stack available (`metaflow-dev`) for metadata service mode.
3. Run commands from repository root:

```bash
cd /home/rawad/metaflow
```

## 1) Start Metadata Service (Dev Stack)

Terminal A:

```bash
metaflow-dev up
```

Keep this terminal running.

Terminal B:

```bash
metaflow-dev shell
```

This shell should include service-related Metaflow config.

Optional sanity check:

```bash
python -c "from metaflow import get_metadata; print(get_metadata())"
```

You should see a `service@...` metadata selector.

## 2) Run Local Metadata Case (manual)

Use a regular shell (not required to be `metaflow-dev shell`):

```bash
cd /home/rawad/metaflow
python metadata_probe_flow.py run \
  --metadata=local \
  --startup-pause-secs 15 \
  --branch-count 3 \
  --branch-sleep-secs 8 \
  --post-join-pause-secs 8 \
  --enable-retry-probe True \
  --fail-in-step none
```

Note the run id from flow output (`run_id=...`).

### Collect in-flight snapshots (local)

In another terminal while the flow is running:

```bash
cd /home/rawad/metaflow
python collect_metadata_snapshots.py \
  --flow-name MetadataProbeFlow \
  --run-id <LOCAL_RUN_ID> \
  --metadata local@. \
  --namespace none \
  --interval-secs 2 \
  --samples 25 \
  --output-file local_snapshots.json
```

If your local metadata root differs, use `local@<path_to_project_root>` accordingly.

## 3) Run Service Metadata Case (manual)

Use the `metaflow-dev shell` terminal:

```bash
cd /home/rawad/metaflow
python metadata_probe_flow.py run \
  --metadata=service \
  --startup-pause-secs 15 \
  --branch-count 3 \
  --branch-sleep-secs 8 \
  --post-join-pause-secs 8 \
  --enable-retry-probe True \
  --fail-in-step none
```

Note this run id (`<SERVICE_RUN_ID>`).

### Collect in-flight snapshots (service)

In another terminal (same shell or any shell with access to service URL):

1) Get service URL:

```bash
echo "$METAFLOW_SERVICE_URL"
```

2) Collect snapshots:

```bash
cd /home/rawad/metaflow
python collect_metadata_snapshots.py \
  --flow-name MetadataProbeFlow \
  --run-id <SERVICE_RUN_ID> \
  --metadata "service@${METAFLOW_SERVICE_URL}" \
  --namespace none \
  --interval-secs 2 \
  --samples 25 \
  --output-file service_snapshots.json
```

## 4) Compare Observed Metadata

```bash
cd /home/rawad/metaflow
python compare_metadata_snapshots.py \
  --local-file local_snapshots.json \
  --service-file service_snapshots.json \
  --output-file snapshot_comparison.md
```

Review:
- `local_snapshots.json`
- `service_snapshots.json`
- `snapshot_comparison.md`

## 5) Suggested Manual Scenarios

Run each scenario in both local and service modes and compare outputs.

### Scenario A: Baseline success with retry

Use:
- `--enable-retry-probe True`
- `--fail-in-step none`

Look for:
- first attempt failure + second attempt success in branch 0
- when `finished/successful/finished_at` become visible

### Scenario B: Failure before end step

Use:
- `--fail-in-step post_join`

Look for:
- whether run is clearly marked as failed and/or finished
- whether end step appears
- differences in task-level fields (`attempt_ok`, `finished`, `successful`)

### Scenario C: End step failure

Use:
- `--fail-in-step end`

Look for:
- behavior of run-level `finished/successful/finished_at`
- visibility and semantics of the failed end task

## 6) What to Document for Maintainer

For each scenario, capture:
1. Exact command used.
2. Run IDs (local + service).
3. Final run-level fields:
   - `finished`
   - `successful`
   - `finished_at`
4. Task-level differences:
   - `current_attempt`
   - `attempt_ok`
   - `finished`
   - `successful`
5. Any visibility lag during polling (state appears later in one backend).
6. Any missing or inconsistent step/task entries.

This should be enough to discuss severity and decide whether behavior is an expected implementation detail or a bug worth fixing.
