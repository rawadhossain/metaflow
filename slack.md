Hi! I’ve been digging into the decorator lifecycle hooks issue and mapping how hooks like step_init, runtime_step_cli, and task_pre_step are executed across decorators.py, runtime.py, and task.py.

I had a few design questions while exploring:

Currently decorator hooks execute in deterministic source order, but this seems to be an implicit behavior rather than a guaranteed contract. Would it make sense to formalize ordering (e.g., via an optional priority attribute) while keeping existing behavior as the default?

I also noticed quite a bit of repeated patterns across hooks (for example MetaDatum registration in several decorators). Would reducing these patterns via helper utilities be considered within scope for this issue?

Should improvements here mainly focus on internal decorators, or also consider ergonomics for third-party decorators?

I noticed the workaround in @parallel around task_pre_step ordering — if ordering guarantees were introduced, would simplifying cases like this be desirable, or is avoiding cross-decorator ordering dependencies still the preferred approach?