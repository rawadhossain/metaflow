# Metaflow CLI Extensibility - Clarifying Questions for Maintainer

These questions are designed to narrow scope before finalizing a production PR.

1. **Priority scope:** Which direction is more valuable for this issue's first iteration?
   - Lifecycle hooks around `start()` initialization
   - Extensible `run`/`resume` option registration for decorators
   - CLI arg serialization cleanup (shared utility)

2. **Backward-compatibility bar:** Should new extension points be strictly additive only, with zero behavior changes for existing flows and extensions?

3. **TL plugin intent:** Is it acceptable to use `TL_PLUGINS` as the host for optional CLI lifecycle hooks, or would you prefer a dedicated plugin category for CLI lifecycle?

4. **Run option extension model:** For flow decorators, should run-level options be:
   - Decorator-scoped (`FlowDecorator.run_options`) and opt-in per flow
   - Global plugin options independent of flow decorators

5. **Lifecycle phases:** Are these initial phases suitable: `post_datastore`, `post_metadata`, `post_decorators`, `post_start`?
   - If not, which phase boundaries are most useful for extensions?

6. **Error handling policy:** If a lifecycle plugin hook fails, should CLI:
   - Fail fast (current PoC behavior)
   - Warn and continue

7. **Testing expectations:** For acceptance, do you want unit-only coverage first, or should we add integration tests under core flow tests as well?

8. **Follow-up preference:** If accepted, would you rather merge:
   - One focused PR per improvement area, or
   - A single PR with all agreed changes
