# Decorator Lifecycle Hooks: Implementation-Driven Plan

## Investigation Findings (completed)

### Ordering: deterministic but implicit

Decorator hooks execute in **source order** (bottom-to-top, closest to `@step` first). All hooks in [task.py](metaflow/task.py) and [runtime.py](metaflow/runtime.py) iterate `for deco in decorators:` over the same list. The order is stable for a given flow definition but is an implicit contract — it can shift when decorators are added via `--with`, mutators, or extensions.

The `@parallel` decorator ([parallel_decorator.py:66-75](metaflow/plugins/parallel_decorator.py)) explicitly documents this problem: it avoids `current._update_env` in `task_pre_step` because compute decorators may not have set the env vars yet. It uses a lazy property workaround instead.

All other cross-decorator lookups in `step_init` are order-independent (they scan the full `decos` list).

### Duplicated pattern inventory (quantified)


| Pattern                                   | Hook             | Decorators using it                                | Lines duplicated |
| ----------------------------------------- | ---------------- | -------------------------------------------------- | ---------------- |
| MetaDatum + register_metadata             | task_pre_step    | 7 (batch, k8s, parallel, argo, SF, airflow, conda) | ~56              |
| Store self.metadata / self.task_datastore | task_pre_step    | 3 (batch, k8s, card)                               | ~6               |
| Sidecar start (logs + spot)               | task_pre_step    | 2 (batch, k8s)                                     | ~16              |
| current._update_env (tempdir, spot)       | task_pre_step    | 2 (batch, k8s)                                     | ~12              |
| Local metadata sync + sidecar terminate   | task_finished    | 2 (batch, k8s)                                     | ~9               |
| Package args append                       | runtime_step_cli | 2 (batch, k8s)                                     | ~6               |
| Store logger/environment/step/datastore   | step_init        | 2-5 (batch, k8s, conda, ...)                       | ~16              |
| **Total**                                 |                  |                                                    | **~121**         |


The MetaDatum registration pattern is the **highest-impact abstraction target** (7 decorators, ~56 duplicated lines).

---

## Implementation Plan

### Phase 1: Ordering guarantee via ORDER_PRIORITY

**Goal**: Make decorator execution order explicit and stable without breaking any existing behavior.

**Where to sort — single location, not per-hook**: The decorator list must be sorted **once** after it is fully assembled, not at every hook call site. The call sequence is:

1. `_attach_decorators(flow, decospecs)` — adds `--with` and env decorators ([cli.py:626](metaflow/cli.py), [run_cmds.py:56](metaflow/cli_components/run_cmds.py))
2. `_init(flow)` — calls `external_init()` on all decorators
3. `_init_graph()` — rebuilds the DAG
4. `**_init_step_decorators()`** — runs mutators, then calls `step_init` on each decorator

The sort should happen inside `_init_step_decorators` in [decorators.py](metaflow/decorators.py), **after** mutators have run (lines 846-871, which may add/remove decorators) but **before** the `step_init` loop (line 876). This is the single chokepoint where the list is finalized. After sorting, the list is written back to `step.decorators`, so all downstream hook call sites in `task.py` and `runtime.py` automatically use the sorted order without any changes.

**File to modify**: [metaflow/decorators.py](metaflow/decorators.py) only.

**Implementation**:

```python
# In _init_step_decorators, after mutators run and _init_graph() is called, before step_init loop:
for step in flow:
    step.decorators = [
        d for _, d in sorted(
            enumerate(step.decorators),
            key=lambda x: (getattr(x[1], "ORDER_PRIORITY", 0), x[0])
        )
    ]
```

Also apply the same sort in `_process_late_attached_decorator` ([decorators.py:893](metaflow/decorators.py)). This function is called from 5 places (conda, pypi, step-functions CLI, argo CLI, airflow CLI) when decorators are attached after the initial `_init_step_decorators` has already run. The sort must happen **after** `external_init()` (line 904-907) but **before** the `step_init` loop (line 909). For each step `s` whose decorators include a newly attached one, re-sort `s.decorators`:

```python
for s in flow:
    if any(deco.name in deco_names for deco in s.decorators):
        s.decorators = [
            d for _, d in sorted(
                enumerate(s.decorators),
                key=lambda x: (getattr(x[1], "ORDER_PRIORITY", 0), x[0])
            )
        ]
```

Without this, a late-attached decorator with a non-default priority would be appended at the end regardless of its `ORDER_PRIORITY`, creating ordering inconsistencies. Since both `_init_step_decorators` and `_process_late_attached_decorator` use the same sort logic, we should extract it into a small helper (e.g., `_sort_step_decorators(step)`) to avoid duplication.

**Key design decisions**:

- `ORDER_PRIORITY = 0` on `StepDecorator` base class — zero behavioral change for all existing decorators
- Stable sort with `(ORDER_PRIORITY, original_index)` preserves source order when priorities are equal
- Sort happens once at finalization, not per-hook — no duplicated logic, no inconsistency risk
- The `@parallel` decorator could then set a priority that ensures it runs after compute decorators, potentially removing the lazy-property workaround

**Validation**: Run the existing test suite; verify `@parallel` + `@kubernetes`/`@batch` stacking still works.

### Phase 2: MetaDatum registration helper

**Goal**: Eliminate the most-duplicated boilerplate — the MetaDatum pattern used by 7 decorators.

**File to modify**: [metaflow/decorators.py](metaflow/decorators.py) — add a helper method to `StepDecorator`:

```python
def _register_metadata(self, metadata, run_id, step_name, task_id, meta_dict, retry_count):
    entries = [
        MetaDatum(field=k, value=v, type=k, tags=["attempt_id:{0}".format(retry_count)])
        for k, v in meta_dict.items()
        if v is not None
    ]
    if entries:
        metadata.register_metadata(run_id, step_name, task_id, entries)
```

**Files to refactor**: All 7 decorators that use this pattern:

- [batch_decorator.py](metaflow/plugins/aws/batch/batch_decorator.py)
- [kubernetes_decorator.py](metaflow/plugins/kubernetes/kubernetes_decorator.py)
- [parallel_decorator.py](metaflow/plugins/parallel_decorator.py)
- [argo_workflows_decorator.py](metaflow/plugins/argo/argo_workflows_decorator.py)
- [step_functions_decorator.py](metaflow/plugins/aws/step_functions/step_functions_decorator.py)
- [airflow_decorator.py](metaflow/plugins/airflow/airflow_decorator.py)
- [conda_decorator.py](metaflow/plugins/pypi/conda_decorator.py)

**Validation**: Each refactored decorator must produce identical MetaDatum entries. Existing tests must pass.

### Phase 3: Evaluate compute decorator shared logic

**Goal**: Determine whether batch/k8s duplication warrants a shared mixin or base class, or whether simpler helper methods suffice.

This is exploratory — the batch and k8s decorators share ~40 lines of duplicated logic across `task_pre_step`, `task_finished`, and `runtime_step_cli`. But they also have significant unique logic. Options to prototype:

- **Option A**: Shared helper methods on `StepDecorator` (e.g., `_sync_metadata_if_local`, `_start_sidecars`, `_stop_sidecars`)
- **Option B**: A `ComputeDecoratorMixin` that both `BatchDecorator` and `KubernetesDecorator` inherit from
- **Option C**: Leave as-is if the coupling would be more harmful than the duplication

We prototype Options A and B, evaluate which fits better, and may discard one or both if the added complexity isn't justified.

### Phase 4: Validation and testing

- Run the full existing test suite against all changes
- Add targeted unit tests for:
  - `ORDER_PRIORITY` sorting behavior (default priority, custom priority, stable sort tie-breaking)
  - `_register_metadata` helper (correct MetaDatum generation, None filtering)
- Verify backwards compatibility: a custom `StepDecorator` subclass that overrides no new methods must work identically

### Phase 5: Proposal write-up (iterative)

Write the maintainer-facing proposal as a fork issue, incorporating:

1. **Findings** from investigation (ordering behavior, cross-decorator dependencies, pattern inventory)
2. **What was implemented** and why (each phase's rationale and results)
3. **What was considered but rejected** (and why — e.g., dependency graphs, sub-phase splitting)
4. **Clarifying questions** that emerged during implementation:
  - Is source-order a public API contract or an implementation detail?
  - Should the focus be on internal decorator cleanup, extension author ergonomics, or both?
  - Is `ORDER_PRIORITY` acceptable, or does the maintainer prefer a different mechanism?
  - Are there hooks beyond `runtime_step_cli` and `task_pre_step` where patterns should be abstracted?
  - For `@parallel` specifically — should the ordering fix replace the lazy-property workaround?
  - Would a `ComputeDecoratorMixin` for batch/k8s be welcome, or is the current approach preferred?

The proposal evolves as prototypes confirm or refute assumptions.

## Todos
Add _register_metadata helper to StepDecorator base class; refactor the 7 decorators that use the MetaDatum pattern to call it

Evaluate whether shared helpers or a mixin for batch/k8s can reduce task_pre_step and task_finished duplication

Run existing tests to confirm all changes are backwards-compatible; add targeted tests for ordering and helper behavior

Write maintainer-facing proposal document on fork, incorporating findings from prototyping; include clarifying questions