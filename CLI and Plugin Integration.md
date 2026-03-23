# CLI and Plugin Integration  
To support the new standalone UI, we will extend Metaflow’s CLI. The `metaflow/cli.py` uses Click’s `@click.group` (with a `LazyGroup`) to register commands like `run`, `step`, `resume`, etc. We should add a `ui` command in this group. For example, insert an entry like `"ui": "metaflow.cli_components.ui_cmd.ui"` in the `lazy_subcommands` dict (or add `@cli.command("ui")`). This means creating a new `metaflow/cli_components/ui_cmd.py` that defines the `ui` command. That command will parse any flags (e.g. port, host) and launch the local server. The CLI framework already handles options like `--datastore` and `--metadata`; for local UI mode we’d force `metadata=local` and a local datastore. In short, we integrate with the existing plugin system: either directly in `cli.py` or by using `metaflow/plugins/` to add a new command. The rest of `cli.py` (the large `start()` function) sets up the flow context (graph, environment, datastore). We won’t use it for UI, except perhaps to pick up config defaults. Instead, our `ui` handler will bypass flow execution and start the web API (details below).  

# Client API – Reading Local Data  
The core logic for accessing local runs is already in Metaflow’s client API. For example, you can do:  
```python
from metaflow import Metaflow
print(Metaflow().flows)   # lists all flow names in the local datastore【75†L79-L84】  
```  
This uses `FlowDataStore` internally. You can instantiate a specific run by name:  
```python
from metaflow import Run
run = Run('MyFlow/1')    # object representing run ID 1 of flow "MyFlow"【119†L130-L134】  
print(run.finished)       # True/False
```  
And you can access steps and artifacts via `Step` and its `.task.data`:  
```python
from metaflow import Step
print(Step('MyFlow/1/a').task.data.result)  # value of artifact 'result' from step 'a'【119†L155-L162】  
```  
These client calls (`Metaflow().flows`, `Run('Flow/ID')`, `Step('Flow/ID/step')`) transparently read from the local `.metaflow` directory. We will use them in our adapter’s endpoints. In practice, the adapter will call these methods under the hood. For instance, a request to list runs would trigger something like `Flow('MyFlow').runs()`, and a request for logs would open the task’s log file (via `task.stdout` / `task.stderr` or reading from disk). The key is: **the client API already supports local mode**, so no new logic is needed for data retrieval beyond invoking these methods. The output can then be serialized to JSON for the UI.  

# Mapping UI Endpoints to Data  
The React UI expects certain REST endpoints (as in the Metaflow Service). We need to replicate these with our local adapter. Likely endpoints include:  
- **GET `/flows`** – Return a list of flow names. Implementation: `return [f.name for f in Metaflow().flows]`.  
- **GET `/flows/{flow}/runs`** – Return run IDs, statuses, parameters, and metrics for flow `{flow}`. Implementation: use `Flow(flow_name).runs()`, and for each run extract properties like `run.id, run.finished, run.tags, run.data.X` etc.  
- **GET `/flows/{flow}/runs/{run}/steps`** – Return a list of steps and their status. Implementation: `Run(flow+"/" + run_id).steps()`, then for each `step`, list `step.name`, `step.finished`, etc.  
- **GET `/flows/{flow}/runs/{run}/steps/{step}/tasks`** – If needed, list tasks (for foreach steps). Implementation: `Step(flow+"/"+run_id+"/"+step_name).tasks()`.  
- **GET `/flows/{flow}/runs/{run}/steps/{step}/log`** – Return the log for that step. Implementation: read the `*.txt` log file from disk or use `task.stderr` (the client may have a convenience property for the log).  
- **GET `/compare?flows={flow}&runs={run1},{run2}`** – For run comparison (stretch goal), return diff of parameters/artifacts. Implementation: fetch both `Run` objects and compare fields (this is optional).  

In each case, the backend will format the objects’ properties into JSON. For example, `Run.id`, `Run.user_tags`, `Run.system_tags`, `Run.data.metric1`, etc., and `Step.name`, `Step.finished`, `Step.start_time`, etc. These fields correspond to those the UI already displays. (The Metaflow client API makes these easily accessible.) We ensure the JSON structure matches what the UI expects from the service; for example, if the UI expects `{ name: ..., status: ... }` for a step, we produce that JSON from `Step` properties.  

# Local Adapter and Server Design  
The minimal adapter is a small web server (e.g. with [FastAPI](https://fastapi.tiangolo.com) or Flask). Its sole job is to translate HTTP requests into Metaflow client calls. For instance:  

```python
from fastapi import FastAPI
from metaflow import Metaflow, Run, Step

app = FastAPI()

@app.get("/api/v1/flows")
def list_flows():
    return {"flows": [flow.name for flow in Metaflow().flows]}

@app.get("/api/v1/flows/{flow}/runs")
def list_runs(flow):
    flow_obj = Metaflow().flows.get(flow)
    return {"runs": [r.id for r in flow_obj.runs()]}

@app.get("/api/v1/flows/{flow}/runs/{run}/steps")
def list_steps(flow, run):
    run_obj = Run(f"{flow}/{run}")
    return {"steps": [{"name": s.name, "finished": s.finished} for s in run_obj.steps()]}

@app.get("/api/v1/flows/{flow}/runs/{run}/steps/{step}/log")
def get_log(flow, run, step):
    s = Step(f"{flow}/{run}/{step}")
    return {"log": s.task.stdout}  # or read from file
```

This is a sketch; the real implementation would handle errors, return more fields, and possibly stream logs. Once this server is implemented, it can be started inside the new `metaflow ui` CLI command (for example, using `uvicorn.run(app, ...)`). The CLI command would set `METAFLOW_SERVICE` to point to `http://localhost:<port>/` and then open the web UI (or instruct the user to visit it).  

# Testing and Validation  
We should draft tests to ensure the adapter works. **Unit tests** can mock or use a temporary local datastore. For example, create a small flow, run it once, and then call the API functions directly (e.g. via FastAPI’s TestClient) to check the JSON output. Ensure that `/api/v1/flows` returns the flow name, `/runs` returns the run ID, and so on. **Integration tests** (using Cypress or similar) can run the actual UI in a headless browser, point it at the local server (`METAFLOW_SERVICE` env), and verify the UI displays the runs correctly and updates live as a flow executes. We should also test edge cases: what if no runs exist, or a run has many artifacts.  

In summary, the **key changes in the `metaflow` repo** are:  
- Add a new CLI command `ui` (either in `cli.py` or as a plugin) that launches the local server.  
- Possibly add a new source file (e.g. `cli_components/ui_cmd.py`) with the server logic.  
- Ensure the CLI’s configuration step (in `start()`) recognizes local mode (set `metadata="local"`) or override it in the `ui` command.  
- Use existing client API (`Metaflow`, `Run`, `Step` classes) to read data.  
- Make sure the new endpoints mirror what `metaflow-ui` expects.  

These steps will connect the pieces: the UI will “think” it’s talking to the Metaflow Service, but in reality it’s hitting our local Python adapter that reads from `.metaflow`. This satisfies the requirement of viewing runs locally without deploying a backend. 

**Sources:** The Metaflow client API documentation shows how to instantiate `Flow`, `Run`, and `Step` objects to access data【119†L130-L134】【119†L155-L162】. For example, `Run('FlowName/1')` and `Step('FlowName/1/a').task.data.x` let us pull run status and artifact values. We will use these calls inside our adapter. The design above is derived from these examples and the existing service-mode behavior. The GSoC project goals also outline that we need to *“view runs from the local datastore”* and *provide a single command to launch (`metaflow ui`)*【91†L287-L290】, which guided this plan. 

