# Metaflow CLI Extensibility Proposal (Issue Draft)

## Background

Metaflow currently exposes two CLI surfaces:

- **Per-flow CLI** (`python myflow.py ...`) centered on `metaflow/cli.py`
- **Global CLI** (`metaflow ...`) centered on `metaflow/cmd/main_cli.py`

The per-flow CLI already supports plugin command groups via `LazyPluginCommandCollection` and `CLIS_DESC`. The global CLI already supports command extension via `CMDS_DESC`.

The problem is not "no extension support", but rather that some high-value paths are still difficult to extend safely.

## Non-Customizable Areas Identified

1. **Monolithic startup lifecycle in `start()`**
   - `metaflow/cli.py` performs datastore, metadata, environment, decorator, monitor, and config setup in one flow.
   - Extension authors cannot inject code at stable lifecycle checkpoints.

2. **Closed run/resume option stack**
   - `metaflow/cli_components/run_cmds.py` defines fixed `common_run_options` and `common_runner_options`.
   - Flow decorators can contribute top-level options today, but cannot add dedicated `run`/`resume` options.

3. **Duplicated CLI argument serialization logic**
   - `metaflow/cli_args.py` and `metaflow/runtime.py` both serialize option dictionaries into CLI args with overlapping, slightly different logic.
   - This increases maintenance overhead and extension complexity.

## Proposed Improvements (Additive)

### A) Lifecycle hooks for CLI startup phases

Add optional lifecycle callbacks to top-level plugins:

- `post_datastore`
- `post_metadata`
- `post_decorators`
- `post_start`

Mechanism:
- Reuse `plugins.TL_PLUGINS` as an additive extension point.
- If a plugin exposes `cli_init(phase, ctx)`, it is called at those checkpoints.

Compatibility:
- Existing TL plugins without `cli_init` are unaffected.
- No behavior change unless hooks are explicitly implemented.

### B) Decorator-driven run/resume option extension

Add a new optional field in `FlowDecorator`:

- `run_options = {}`

Mechanism:
- Extend `common_run_options` to include `FlowDecorator.run_options` for the current flow.
- Preserve existing `FlowDecorator.options` behavior for top-level options.

Compatibility:
- Existing decorators do not need updates.
- Existing command options remain unchanged.
- New options are additive and opt-in.
- Run option names are normalized (`--foo` and `foo` map to `--foo`) and collisions
  are checked using Click-style param names (dash/underscore equivalent), preventing
  accidental duplicates.

### C) Shared CLI arg serializer for runtime + CLIArgs singleton

Add a shared helper in `metaflow/util.py`:

- `dict_to_cli_args(...)`

Mechanism:
- `metaflow/cli_args.py` and `metaflow/runtime.py` both delegate to this helper.
- Preserve current semantics including:
  - boolean handling
  - `decospecs -> --with`
  - config option expansion
  - tuple/list handling

Compatibility:
- Behavior remains backward-compatible while reducing duplicate code paths.

## What We Are Not Changing in This Iteration

- Plugin command registration model (`CLIS_DESC`, `CMDS_DESC`)
- Existing decorator registration flow (`STEP_DECORATORS`, `FLOW_DECORATORS`)
- Core command names and dispatch structure

## Suggested Rollout

1. Merge additive hooks + run option extension + serializer unification behind current defaults.
2. Add unit tests for each feature.
3. Request maintainer feedback on:
   - phase naming
   - error policy for failing lifecycle hooks
   - whether TL plugins remain the right host long-term.

## Expected Benefits

- Cleaner extension path without forcing plugin authors to fork core CLI internals.
- Lower maintenance cost from deduplicated argument serialization.
- Better long-term ergonomics for Metaflow extension authors.
