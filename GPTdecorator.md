# ChatGPT's take on the [DecoratorIssue.md](./DecoratorIssue.md):
**Note:** chatgpt does not have the full context of the codebase nor the complete documentation of Metaflow, it might not always direct to the right direction of resolving issue, also it may over engineer the things that are not intended. SO make your own judgement. Your should follow the codebase pattern and practices and arch-docs mentioned `arch-docs folder` in root directory.

# 1) Short summary (what the issue is)

Metaflow’s decorator system exposes *lifecycle hooks* (e.g. `step_init`, `runtime_step_cli`, `task_pre_step`, etc.). Those hooks are strictly defined in *what stage* they run in, but there is **no stable guarantee on the ordering between different decorators’ hooks that run in the same stage**. The issue asks to:

- Explore existing lifecycle hooks and patterns,
- Decide whether to add new hooks or change semantics to support common patterns,
- Propose changes that enable dependable ordering or abstractions for common patterns, while preserving backwards compatibility.

Put simply: decorators sometimes need to interoperate (one decorator expects another to have done X in the same lifecycle phase), but current hook ordering is unreliable — the issue is about making that safer, or offering abstractions so cross-reliance is not needed.

# 2) Why this matters (technical consequences)

- **Race/coupling bugs:** If decorator A assumes B’s `step_init` has already run, but ordering flips, A can fail or misconfigure.
- **Hard-to-debug timing bugs:** These show up only sometimes and are brittle across versions and environments.
- **Distributed runs:** Ordering guarantees are harder when parts run in different processes or on different hosts.
- **API stability:** Any change must avoid breaking existing decorators or user code.

# 3) Typical patterns observed (from the issue text + what you already know)

- Decorators adding CLI options at runtime (`runtime_step_cli`).
- Decorators performing per-task setup right before step execution (`task_pre_step`).
- Decorators that install/seed shared context or register side effects during `step_init`.
    
    These patterns frequently need a reliable ordering or an abstraction so that “I want to contribute a CLI option / pre-step action / shared resource” is simple and composable.
    

# 4) Concrete solutions (design space) — tradeoffs included

### A — Leave implicit and document recommended practices

- **What:** Do nothing to ordering; document that decorators must be independent and avoid cross-dependencies.
- **Pros:** No compatibility risk, simplest.
- **Cons:** Doesn’t fix the real problem; fragile for users.

### B — Stable ordering by registration order

- **What:** Execute all decorators’ hooks in the deterministic order they were registered (e.g., decorator application order or a sorted stable list).
- **Pros:** Minimal, predictable, easy to implement.
- **Cons:** Registration order is an implicit contract — brittle and non-obvious; still can require authors to carefully craft decorator order.

### C — Priority / phase levels for hooks (recommended minimal change)

- **What:** Allow decorators to register hooks with a numeric `priority` or named *phase* (e.g. `PRE_INIT`, `INIT`, `POST_INIT`). Hooks within the same phase are ordered by priority (lower first) and then stable tie-breaker (e.g., registration order).
- **Pros:** Explicit, simple to reason about, backwards-compatible if default priority = 0 and default phase = existing stage.
- **Cons:** Adds API parameter to decorator registration; doesn’t express dependency on a *named* other decorator.

### D — Declarative dependencies between decorators

- **What:** Decorators declare `depends_on=['other_decorator_name']` or `provides=['some_capability']`. Execution engine topologically sorts.
- **Pros:** Explicit intent and robust ordering when dependences are acyclic.
- **Cons:** More complex, requires a canonical name for decorators, cycles must be handled, more breaking surface.

### E — Coordinator-based orchestration for distributed scenarios

- **What:** A centralized runtime (or metadata store) coordinates ordering across processes (e.g. write “hook X finished” to metadata and others wait).
- **Pros:** Can provide global ordering across machines.
- **Cons:** Much more complex, latency and reliability concerns; may be overkill for many patterns.

### F — Higher-level abstractions / helpers for common patterns

- **What:** Instead of changing ordering, provide utilities that let decorators register CLI fragments, merge pre-step actions, or attach to a shared context in a safe composable way.
- **Pros:** Low risk, useful immediately, avoids forcing a global ordering model.
- **Cons:** Doesn’t eliminate all ordering use-cases.

# 5) Recommendation (balanced, pragmatic)

I recommend a two-track approach:

1. **Immediate, low-risk wins:** implement *helper abstractions* for the most common patterns:
    - a safe `runtime_cli_registry` that lets decorators *contribute* CLI arguments and resolves conflicts deterministically (merge strategy, name collisions reported).
    - a `pre_step_registry` to collect pre-step callables that will be executed in a deterministic, documented order (e.g. registration order). These callables receive a shared context object.
    - a shared context object passed into hooks so related data can be shared without relying on ordering (e.g. `context.shared['s3_client'] = ...`).
2. **Medium-term improvement:** add **priority/phase** metadata to hook registration:
    - default keeps current semantics (no visible change).
    - decorators can opt-in to set `priority` or `phase` if they need ordering.
    - execution rules: sort by `(phase_order, priority, registration_order)`.
    - this covers many real-world needs with minimal complexity and good backward compatibility.
3. **Long-term (only if necessary):** support declarative `depends_on` only if after adoption we see many real dependencies that aren’t captured by priority/phase. For cross-process ordering needs, consider a limited coordinator mechanism with careful performance testing — but prefer to design for *not* needing global ordering where possible (design decorators to be idempotent and to use shared metadata as coordination when necessary).

# Testing & examples to include in PR

- tiny repo with two decorators where A needs B to run first — show how to do it with `priority` and with `depends_on` (if implemented).
- test merging CLI flags, including collision handling.
- test local single-process runs and multi-machine runs for non-ordered behavior (clarify which guarantees exist only in-process).