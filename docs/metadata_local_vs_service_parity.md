# Local vs Service Metadata Parity Investigation

## Issue

Investigate the issue **"Compare differences in local metadata vs metadata service"** by running the same flow under:

- local metadata (`--metadata=local`)
- metadata service (`--metadata=service`)

and evaluating whether user-visible lifecycle semantics are consistent across backends.

## Investigation

This investigation focuses on **user-visible lifecycle semantics**, not byte-level equality of raw metadata records across independent runs. Differences in identifiers, timestamp values, and event ordering can occur between local and service executions without implying a semantic mismatch. The goal is to verify whether both backends provide sufficient signals to reliably infer:

- run completion
- run success/failure
- task completion
- retry behavior

## Methodology

### Reproducible tools used

- `metadata_probe_flow.py`: a deterministic probe workflow used to exercise the lifecycle states that matter for parity checks. It intentionally includes:
  - a normal success path (to verify terminal success semantics)
  - a controlled failure path (to verify failure visibility and terminal state)
  - a retry probe (to verify retry metadata and attempt transitions)
  - fanout/foreach branches (to ensure multi-task step behavior is represented)
  - sleep windows (to make in-flight polling practical and reproducible)
- `collect_metadata_snapshots.py`: periodically captures run/step/task lifecycle state from the client view, producing JSON timelines that can be compared across backends.
- `compare_metadata_snapshots.py`: generates text comparisons from the collected snapshots to highlight signal matches and differences.

Together, these tools make the investigation reproducible and easy to extend for future contributors.

### Scenarios executed

1. **Baseline success + retry probe**
  - local: `local_snapshots_success.json`
  - service: `service_snapshots_success.json`
  - **Why this scenario**: establishes baseline parity under normal execution while also validating that a first-attempt failure followed by retry success is represented consistently.
2. **Failure scenario (`--fail-in-step post_join`)**
  - local: `local_snapshots_fail_post_join.json`
  - service: `service_snapshots_fail_post_join.json`
  - **Why this scenario**: checks whether both backends expose failure semantics consistently when execution fails before reaching the `end` step.
3. **Mid-run termination experiment**
  - local: `local_snapshots_midkill.json`
  - service: `service_snapshots_midkill.json`
  - **Why this scenario**: probes behavior around interrupted execution to see whether lifecycle signals remain interpretable when the launcher process is terminated.

These scenarios were selected to cover the primary issue questions: completion detection, success/failure interpretation, task terminal state visibility, and retry handling.

## Lifecycle Signal Comparison

The primary signals examined were:

- `run.finished`
- `run.successful`
- `run.finished_at`
- end-task presence (`end_task_exists`)
- task terminal flags (`task.finished`, `task.successful`)
- retry visibility (`current_attempt`, retry transitions)

The comparison emphasizes **semantic parity** (can an observer infer the same lifecycle outcome?) rather than strict equality of raw records across distinct runs.

### Summary of key signals


| Signal                            | Baseline success (local vs service) | Post-join failure (local vs service) | Notes                                                        |
| --------------------------------- | ----------------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| `run.finished`                    | Match (`True` / `True`)             | Match (`False` / `False`)            | No semantic mismatch observed in tested scenarios            |
| `run.successful`                  | Match (`True` / `True`)             | Match (`False` / `False`)            | Consistent with expected run outcome                         |
| `run.finished_at`                 | Both set; timestamps differ         | Both `None`                          | Timestamp value differs because runs are distinct executions |
| `end_task_exists`                 | Match (`True` / `True`)             | Match (`False` / `False`)            | End step absent in failure-before-end scenario               |
| `terminal task lifecycle signals` | Consistent at lifecycle level       | Consistent at lifecycle level        | Task identifiers differ across runs/backends                 |
| Retry behavior                    | Visible and successful in both      | Visible before failure path in both  | Branch retry probe observed in both backends                 |


## Example comparison output

Running `compare_metadata_snapshots.py` on the collected JSON snapshots produces a text report. Below are the run-level portions of that output for the two main scenarios. (The script writes to a file or stdout; these excerpts are what we observed when comparing local vs service snapshots.)

**Baseline success scenario** (comparing final snapshots from a completed run):

```text
- MATCH `finished`: local=True service=True
- MATCH `successful`: local=True service=True
- DIFF `finished_at`: local='...' service='...'
- MATCH `end_task_exists`: local=True service=True
```

**Post-join failure scenario** (comparing final snapshots from a run that failed before the end step):

```text
- MATCH `finished`: local=False service=False
- MATCH `successful`: local=False service=False
- MATCH `finished_at`: local=None service=None
- MATCH `end_task_exists`: local=False service=False
```

These results show that run-level lifecycle signals matched across local and service in both success and failure scenarios, which is the primary parity target for this investigation.

## Timing and snapshot ordering observations

- Requested polling interval was 2 seconds.
- Observed average cadence from collected snapshots:
  - local success: ~1.92s
  - service success: ~12.02s
  - local failure: ~1.95s
  - service failure: ~8.05s

Interpretation:

- Service-backed client polling in this dev setup was noticeably slower than local.
- This affects **when** states are observed, not the terminal semantics observed in tested scenarios.
- Because snapshots are taken at observation time, slower polling can also change which intermediate task states appear in the final collected timeline.

## Why task-level DIFF lines can appear without semantic mismatch

Some task-level differences in comparison output are expected and not necessarily correctness issues:

- Local and service runs use different run/task identifiers (e.g., local timestamp-like IDs vs service integer IDs).
- Comparisons were between separate executions, so task pathspecs do not align one-to-one by raw ID.
- Snapshot timing can capture different in-flight points, producing apparent "missing task" diffs at a given sample.

For this reason, run/step/task **lifecycle semantics** are the primary parity signal, while raw task-path diffs are secondary hints.

## Conclusion

### Issue goals status

1. **Explore differences**: Completed via matched scenario runs, snapshot collection, and report generation.
2. **Report severe differences**: No severe semantic mismatches were found in tested lifecycle scenarios.
3. **Propose changes if needed**:
  - No runtime code change is currently required based on these results.
  - Follow-up investigation is recommended for:
    - service polling latency in dev stack
    - stricter interruption semantics testing (worker/process-level termination)

Overall, in the tested scenarios, local metadata and metadata service provided **similar lifecycle signals**: `run.finished`, `run.successful`, terminal task state, and retry metadata behaved consistently. No semantic mismatches affecting lifecycle interpretation were observed.