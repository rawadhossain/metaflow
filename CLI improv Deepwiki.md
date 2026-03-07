### Below is the analysis by deepwiki on Metaflow CLI improvements issue, source: https://deepwiki.com/search/which-folders-or-files-are-res_dd416782-58af-498f-a362-26c603334a29?mode=deep
**Note**: This may not be 100% accurate, also the plans and Proposed Design are not bound to follow exactly what deepwiki said, it will depend on the actual issue work, current codebase setup and maitnainers vision towards the issue. Make your judgement rather than blindly following deepwiki analysis.

## Metaflow CLI Internals: Files, Pain Points, and Extensibility Design
## **1. Files & Folders Responsible for CLI Internals**

The CLI is split across **two distinct surfaces**: the **per-flow CLI** (invoked as **`python myflow.py run ...`**) and the **global `metaflow` CLI** (invoked as **`metaflow configure`**, etc.).

---

### **A. Per-Flow CLI**

### **`metaflow/cli.py` — The root entry point**

This is the most critical file. It defines two layered command groups:

- **`cli`** — an inner **`LazyGroup`** containing the core built-in subcommands (**`run`**, **`resume`**, **`step`**, **`init`**, **`dump`**, **`spin`**, **`spin-step`**), plus inline commands **`check`**, **`show`**, **`help`**, **`output_raw`**, **`output_dot`**, **`version`**. cli.py:122-135
- **`start`** — the outer **`LazyPluginCommandCollection`** that is actually invoked. It wraps **`cli`** as a source, then lazily loads all plugin CLIs (e.g., **`batch`**, **`kubernetes`**, **`card`**) from **`plugins.get_plugin_cli_path()`**. cli.py:233-350
- The **`start()`** function performs all critical initialization: resolving datastore, environment, metadata, event logger, monitor, configs, flow mutators, and decorator init. It is the gatekeeper for the entire CLI lifecycle. cli.py:333-650
- The **`CliState`** class is a plain bag of attributes set imperatively inside **`start()`**. cli.py:707-709
- **`main()`** is the entry point called from the flow's **`if __name__ == "__main__"`** block. cli.py:712-748

---

### **`metaflow/cli_components/` — Core built-in subcommands**

| **File** | **Commands** |
| --- | --- |
| **`run_cmds.py`** | **`run`**, **`resume`**, **`spin`** |
| **`step_cmd.py`** | **`step`** (internal), **`spin_step`** (internal) |
| **`init_cmd.py`** | **`init`** (internal) |
| **`dump_cmd.py`** | **`dump`** |
| **`utils.py`** | **`LazyGroup`**, **`LazyPluginCommandCollection`** |
- **`common_run_options`** and **`common_runner_options`** are the shared option decorators for **`run`**/**`resume`**. run_cmds.py:91-182
- **`LazyGroup`** lazily imports core built-in subcommands by dotted-path string. utils.py:104-140
- **`LazyPluginCommandCollection`** merges eager **`sources`** (the core **`cli`** group) with lazy-loaded plugin CLI groups, enabling third-party CLI groups. utils.py:6-101
- The **`step`** command has a fully fixed set of click options; third parties cannot inject new options here. step_cmd.py:18-181

---

### **`metaflow/cli_args.py` — Global CLI state singleton (UBF)**

A module-level singleton that records top-level and step-level kwargs so that decorators can reconstruct the exact CLI command for parallel tasks (e.g., UBF). It has hard-coded special cases for **`decospecs`**, **`config`**, and **`config_value`**. cli_args.py:26-93

---

### **`metaflow/decorators.py` — Decorator lifecycle and CLI integration**

- **`FlowDecorator.options`** + **`add_decorator_options()`** is the **primary documented extension point** for adding top-level CLI options from a flow decorator. decorators.py:266-293
- **`FlowDecorator.get_top_level_options()`** propagates those option values to step subprocesses. decorators.py:253-262
- **`StepDecorator.runtime_step_cli()`** is the **primary documented extension point** for decorators that need to mutate the step subprocess command (e.g., redirecting to Kubernetes or Batch). decorators.py:417-423

---

### **`metaflow/runtime.py` — Step subprocess command builder**

- The **`CLIArgs`** class (in **`runtime.py`**, distinct from the one in **`cli_args.py`**) assembles **`top_level_options`** and **`command_options`** for each step subprocess. It is a concrete, non-subclassable class. **`FlowDecorators`** contribute via **`get_top_level_options()`**. runtime.py:2027-2168
- **`Worker._launch()`** is where **`CLIArgs`** is instantiated and where **`deco.runtime_step_cli()`** is called to let decorators mutate the command before **`subprocess.Popen`**. runtime.py:2220-2270

---

### **B. Plugin & Extension Registration**

### **`metaflow/plugins/__init__.py` — Plugin registry**

Declares all built-in plugins via **`*_DESC`** lists (**`CLIS_DESC`**, **`STEP_DECORATORS_DESC`**, **`FLOW_DECORATORS_DESC`**, **`ENVIRONMENTS_DESC`**, etc.) and calls **`process_plugins(globals())`** which merges extension packages into these lists. __init__.py:9-182

**`get_plugin_cli_path()`** returns the dict passed as **`lazy_sources`** to **`start`**, enabling lazy CLI loading. __init__.py:189-190

---

### **`metaflow/extension_support/plugins.py` — Plugin resolution engine**

- **`_plugin_categories`** defines every recognized plugin type, including **`"cli"`** and **`"runner_cli"`**. plugins.py:182-202
- **`process_plugins()`** discovers, merges, and resolves plugins from installed **`metaflow_extensions`** packages. plugins.py:9-83
- **`resolve_plugins()`** converts enabled plugin names to actual classes. plugins.py:121-168

---

### **`metaflow/extension_support/cmd.py` — Global `metaflow` CLI extension**

A **parallel but separate** extension mechanism (independent from **`plugins.py`**) for adding commands to the global **`metaflow`** CLI tool (not the per-flow CLI). cmd.py:1-114

---

### **`metaflow/extension_support/__init__.py` — Extension discovery**

The core of the **`metaflow_extensions`** namespace package discovery and loading mechanism. Defines **`_extension_points`** (the supported directory names in extension packages), including **`"cmd"`**, **`"plugins"`**, **`"toplevel"`**, **`"config"`**, **`"alias"`**, and others. __init__.py:341-351

---

### **C. Global `metaflow` CLI**

### **`metaflow/cmd/main_cli.py` — The `metaflow` tool entry point**

Uses **`process_cmds()`** + **`resolve_cmds()`** (from **`extension_support/cmd.py`**) to assemble the global CLI. Extensions contribute via the **`cmd`** extension point. main_cli.py:66-106

---

## **2. Parts That Are Hard or Impossible to Extend**

### **🔴 Hard: Fixed top-level options on `start`**

The **`start`** command hard-codes all its **`@click.option`** decorators. The only legitimate extension path is via **`FlowDecorator.options`** + **`add_decorator_options()`**, but this requires the user's flow to actually use that **`FlowDecorator`**. There is no way for a third party to add a **global** (flow-agnostic) new top-level option without forking **`cli.py`**. cli.py:233-332

**Workaround today**: **`FlowDecorator.options`** injects options per-flow only. decorators.py:239-263

---

### **🔴 Hard: The `start()` initialization sequence is monolithic**

The body of **`start()`** (resolving datastore, environment, config, metadata, decorators, etc.) is a single large function with no lifecycle hooks. Third parties cannot inject code before/after individual initialization phases (e.g., "after metadata is initialized", "before decorators are applied"). cli.py:333-650

---

### **🔴 Hard: `common_run_options` / `common_runner_options` are closed**

The options for **`run`**, **`resume`**, and **`spin`** are defined as closed decorator stacks. There is no extension point for adding a new option to these commands without modifying **`run_cmds.py`**. A **`FlowDecorator`** can expose its option on **`start`** but not specifically on **`run`**/**`resume`**. run_cmds.py:91-182

---

### **🔴 Hard: The `step` command's options are fully fixed**

The **`step`** command (the internal per-task executor) has a closed set of options. Decorators can mutate the **`CLIArgs`** dict in **`runtime_step_cli()`** to pass new **`command_options`**, but only if the receiving **`step`** command already has a matching **`@click.option`**. New options simply don't get parsed on the other end. step_cmd.py:18-181

---

### **🟡 Partially Hard: The inner `cli` group (`check`, `show`, etc.)**

Commands like **`check`**, **`show`**, **`output_dot`**, **`version`** are defined directly on the **`cli`** group and are not overridable. Plugin CLIs can only add **new** sibling commands to **`start`** (via **`lazy_sources`**), not replace or wrap these inner ones. cli.py:138-228

---

### **🟡 Partially Hard: `CLIArgs` (runtime) is a concrete class**

The **`CLIArgs`** in **`runtime.py`** is not designed for subclassing or middleware patterns. The **`top_level_options`** initialization is imperative, and the only hooks in are **`FlowDecorator.get_top_level_options()`** (which is called but limited to dict updates) and **`StepDecorator.runtime_step_cli()`** (which can mutate the object but only if the caller knows the object's internal structure). runtime.py:2027-2094

---

### **🟡 Partially Hard: Two separate `CLIArgs` singletons with duplicated logic**

The **`CLIArgs`** in **`cli_args.py`** (for UBF) and the one in **`runtime.py`** duplicate the **`_options()`** serialization logic with separate hard-coded special-casing for **`decospecs`**, **`config`**, and **`config_value`**. Extensions that introduce new option semantics must patch both. cli_args.py:62-91 runtime.py:2134-2162

---

### **🟡 Partially Hard: `CliState` is an unstructured bag**

**`CliState`** is an opaque object with attributes set ad-hoc inside **`start()`**. Third-party plugins and decorators rely on knowing the internal attribute names (**`ctx.obj.flow`**, **`ctx.obj.environment`**, etc.) as an informal contract. There is no schema, no lifecycle for third-party **`CliState`** contributions, and no way to declare a dependency on a value being initialized before yours. cli.py:707-709

---

## **3. Proposed Design for Extensibility**

Here is a layered proposal preserving full backward compatibility:

---

### **✅ A. `CLIPlugin` lifecycle protocol for `start` initialization hooks**

**Problem**: **`start()`** is monolithic.

**Proposal**: Introduce a **`TLPlugin`** (top-level plugin) protocol, similar to how **`TL_PLUGINS_DESC`** already exists in **`plugins/__init__.py`**, but specifically for CLI lifecycle. Each **`TLPlugin`** would be called at named phases inside **`start()`**:

```
start()
  ├─ phase: "pre_init"        → before any object is created
  ├─ phase: "post_datastore"  → after datastore and env are set up
  ├─ phase: "post_metadata"   → after metadata provider is ready
  ├─ phase: "post_decorators" → after _init_flow_decorators + _init_step_decorators
  └─ phase: "post_start"      → just before invoking the subcommand
```

**`TL_PLUGINS_DESC`** already exists: __init__.py:174-180

Extending it with a **`cli_lifecycle`** protocol (e.g., **`def cli_phase(phase: str, ctx: click.Context) -> None`**) would be backward compatible.

### **✅ B. `FlowDecorator.run_options()` for per-command option injection**

**Problem**: **`FlowDecorator.options`** injects into **`start`**, but there's no way to inject into **`run`**/**`resume`** specifically.

**Proposal**: Add an optional **`run_options`** dict to **`FlowDecorator`** (similar to **`options`**), and extend **`common_run_options`** to read from all registered flow decorators (via the flow class stored in **`current_flow`**), appending their options. This mirrors the **`add_decorator_options`** pattern already used for **`start`**: decorators.py:266-293

The **`run`** and **`resume`** commands already accept **`**kwargs`** so their signatures can absorb new options without breaking changes: run_cmds.py:367-378

---

### **✅ C. `CLIArgs` middleware / mutator list**

**Problem**: **`CLIArgs`** (runtime) is a closed class.

**Proposal**: After calling **`runtime_step_cli()`** on all step decorators, also call a new hook **`runtime_top_level_cli(args)`** on all **flow** decorators. This hook would be allowed to mutate **`args.top_level_options`** (currently only **`get_top_level_options()`** does this, but only at construction time). More powerfully, expose a list of registered **`CLIArgsMiddleware`** callables (contributed via **`TL_PLUGINS_DESC`**) that are called in order before **`get_args()`** is assembled: runtime.py:2240-2247

---

### **✅ D. Unify the two `CLIArgs` classes**

**Problem**: Two separate classes with duplicated **`_options()`** logic and independent special-casing.

**Proposal**: Extract the **`_options()`** serialization into a single utility function in **`metaflow/util.py`** (a **`dict_to_cli_options()`** that handles **`decospecs`**, **`config-value`**, and user-extensible special cases via a registry). Then have both **`cli_args.py`** and **`runtime.py`**'s **`CLIArgs`** delegate to it. The comment in **`runtime.py`** already acknowledges this debt: runtime.py:2134-2136 cli_args.py:1-14

---

### **✅ E. Structured `CliState` with declared contributors**

**Problem**: **`CliState`** is an unstructured bag.

**Proposal**: Introduce a **`CliStateContributor`** interface (similar to **`TLPlugin`**) that extensions can implement to declare what they add to **`ctx.obj`** and when. A **`CliState`** registry would call **`contributor.contribute(ctx)`** at the appropriate phase, and contributors could declare dependencies on other contributors. Backward compatible: existing direct attribute assignments on **`ctx.obj`** continue to work. cli.py:707-709

---

## **Summary Table**

| **Area** | **File(s)** | **Extensibility Today** | **Proposed Fix** |
| --- | --- | --- | --- |
| **`start`** top-level options | **`cli.py`** | FlowDecorator.options only (flow-specific) | Global **`TLPlugin.cli_options()`** |
| **`start`** init lifecycle | **`cli.py`** | None | **`TLPlugin`** phase hooks |
| **`run`**/**`resume`** options | **`run_cmds.py`** | None | **`FlowDecorator.run_options()`** |
| **`step`** command options | **`step_cmd.py`** | **`runtime_step_cli()`** mutates subprocess dict | Align dict keys with **`step`** options via registry |
| **`CLIArgs`** (runtime) | **`runtime.py`** | **`get_top_level_options()`** + **`runtime_step_cli()`** | CLIArgs middleware list |
| Two **`CLIArgs`** duplication | **`runtime.py`**, **`cli_args.py`** | None | Shared **`dict_to_cli_options()`** utility |
| **`CliState`** bag | **`cli.py`** | Direct **`ctx.obj.attr`** assignment | **`CliStateContributor`** protocol |
| Inner **`cli`** group commands | **`cli.py`** | Not overridable | Wrap **`cli`** group in a **`LazyGroup`** with extension slots |
| Global **`metaflow`** CLI | **`cmd/main_cli.py`** | **`CMDS_DESC`** / **`cmd`** extension point ✅ | Already good |
| Plugin CLI subcommands | **`plugins/__init__.py`**, **`cli_components/utils.py`** | **`CLIS_DESC`** / **`lazy_sources`** ✅ | Already good |
| Step/Flow decorators | **`decorators.py`**, **`plugins/__init__.py`** | **`*_DECORATORS_DESC`** ✅ | Already good |

## **Notes**

- **Two distinct CLIs**: The per-flow CLI (**`python myflow.py run`**) and the global **`metaflow`** CLI (**`metaflow configure`**) use entirely separate extension mechanisms — **`CLIS_DESC`**/**`LazyPluginCommandCollection`** for the former, and **`CMDS_DESC`**/**`resolve_cmds()`** for the latter. Don't conflate them.
- **Two distinct `CLIArgs` classes**: **`metaflow/cli_args.py`** is a module-level singleton for UBF command replication; **`metaflow/runtime.py`**'s **`CLIArgs`** is instantiated per task in **`Worker._launch()`**. Both exist and are acknowledged as needing unification.
- The **`TL_PLUGINS_DESC` mechanism** already exists and is used for parsers and event name providers — it is the most natural foundation for extending the CLI initialization lifecycle without breaking existing extensions. plugins.py:182-202