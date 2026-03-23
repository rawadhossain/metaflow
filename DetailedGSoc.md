## Metaflow — Standalone Local Mode
**Purpose:** detailed design & implementation plan for adding `metaflow ui` (Standalone Local Mode) to the **Metaflow core repo** (`Netflix/metaflow`).

**Note:** this file focuses *only* on the core repo work: the CLI, a lightweight adapter, metadata access, asset-index building, and live-event streaming. All visualization, UX, and frontend components remain the responsibility of the `metaflow-ui` repo and are only shown here as required consumers of the core adapter API. These are just my initial research, actual current codebase may look different and might need different approach for implementing the standalone local mode

Basically what i haveunderstood, standalone local mode means A lightweight UI adapter enabling local metadata visualization without requiring Metaflow Service deployment.

### What Standalone Mode Is NOT
It is NOT:
- Replacing Metaflow Service
- Building a distributed backend
- Creating a new storage abstraction
- Adding persistent UI-specific database

It is a thin access layer.
Clean Mental Model:

Layer 1: Metaflow Core
    - runs
    - metadata
    - artifacts

Layer 2: UI Adapter (new)
    - converts metadata → UI JSON
    - streams events
    - no business logic

Layer 3: Frontend (metaflow-ui)
    - visualization
    - graphs
    - comparison
    - theming

Metaflow today is: Run-centric. Not asset-centric.
Dagster is asset-centric. Metaflow is step-centric.
So standalone mode must:
1. Parse runs
2. Extract artifacts
3. Build a derived asset graph

This is where most thinking belongs.

 So What Work Actually Belongs in Core?

### Minimal and correct standalone implementation includes:

### ✅ 1. CLI command

Register `metaflow ui`.

### ✅ 2. Metadata reader wrapper

Thin wrapper around:

- LocalMetadataProvider
- get_object APIs

### ✅ 3. Asset index builder (new logic)

This is the biggest real addition.

You will:

- iterate through runs
- collect artifacts
- map artifact → producing step
- map step dependencies → asset dependencies
- build lineage graph structure

This does NOT change storage.

It derives a graph from existing data.

### ✅ 4. Simple HTTP adapter

- REST endpoints
- WebSocket for live updates

## Some in depth analysis regarding this codebase and the expected work for gsoc project:
**1. Problem statement & goals**
Problem: Metaflow's current UI expects a running Metaflow Service (remote backend). Developers with local runs cannot inspect runs, artifacts, or lineage using a single local command.

**Primary goal:** Add a *lightweight*, *non-invasive* capability in Metaflow core to let developers run:
```bash
metaflow ui
```
and immediately open a browser UI that shows *local* runs, artifacts, and a derived asset-lineage graph — without deploying or depending on Metaflow Service.

**Design principles:**
- **Non-invasive:** Do not change metadata format or execution semantics.
- **Thin adapter:** Provide a translation layer exposing a stable JSON + WebSocket API that the UI can consume.
- **Reuse core internals:** Use existing metadata providers (e.g., `LocalMetadataProvider` / internal `get_object` helpers) where possible.
- **Single-command developer UX:** CLI starts adapter, optionally serves or proxies UI static build, and opens the browser.
- **Stateless adapter:** Minimal caching only for performance; persistent changes are not required.
- **Testable & debuggable** with unit tests and integration tests.
# 2. Scope (core repo vs. metaflow-ui)
**Core repo - current codebase (`Netflix/metaflow`) — responsibilities (this file):**
- `metaflow ui` CLI entry.
- A small HTTP adapter (FastAPI/Flask) exposing REST endpoints mapped to Metaflow metadata (runs, steps, artifacts).
- WebSocket or SSE endpoint publishing live-run events (step status, logs, materializations).
- Metadata access wrapper that reuses the repo's `LocalMetadataProvider` or equivalents to read local run/step/task/artifact data.
- Asset indexer: derive an *asset-centric* graph from step-centric run data.
- Minimal static-served UI support (serve a prebuilt `metaflow-ui` bundle) or proxy configuration for dev mode.
- Tests, docs, and examples for maintainers.
**Frontend repo (`Netflix/metaflow-ui`) — responsibilities (not in this file):**
- Graph visualization (lineage graph).
- Live DAG view & streaming logs.
- Run comparison UI.
- Theming, UX, and client-side logic to call the adapter APIs.
- Should work against the adapter contract defined below.
Key notes:
- Adapter is an ephemeral service for local mode. It should **not** be a long-running production replacement for Metaflow Service.
- Adapter must accept a `-metadata-provider` flag (default: `local`) to select appropriate metadata provider/config.
- Adapter must be able to read multiple metadata namespaces (if user has runs in different namespaces or local roots).

## Implementation notes & integration points in codebase
There are existing `LocalMetadataProvider` and internal `get_object_internal` patterns. Reuse them rather than re-parsing files manually. The DeepWiki PDF highlights this pattern and suggests using those helpers.

Relvant research on deepwiki on the metflow repo:
[Search | DeepWiki](https://deepwiki.com/search/is-there-any-command-like-meta_4cbdb4b5-ecfd-42ea-bc0f-c902e7ee4c51)