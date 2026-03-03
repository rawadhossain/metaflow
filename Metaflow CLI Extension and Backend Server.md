# Metaflow CLI Extension and Backend Server  
The “Standalone local mode” feature means adding a new `metaflow ui` command in the Metaflow core that launches a lightweight local server serving run data from the `.metaflow` directory. Metaflow’s Python CLI is based on [Click](https://palletsprojects.com/p/click/) and supports plugins, so one approach is to create a CLI plugin (e.g. under `metaflow/plugins/`) that implements a `ui` group. This command would start a Python web server (e.g. FastAPI or Flask) on localhost, configured to read from the local Metaflow datastore and serve JSON APIs. In effect, the backend adapter will replace the usual Metaflow Service: instead of requiring an external service or database, it reads directly from the user’s `.metaflow` directory. The new `metaflow ui` command bundles this together so that typing `metaflow ui` spins up the local server and optionally opens the browser. This matches the GSoC goal: *“Standalone local mode – view runs from the local Metaflow datastore without requiring Metaflow Service. Single command to launch (e.g., `metaflow ui`).”*【45†L270-L272】【45†L287-L290】.  

# Metaflow Client API for Local Datastore  
Under the hood, the local adapter will use the Metaflow Python Client API to load flows, runs, steps, artifacts, etc. The client library already handles both “remote” (service-backed) and “local” modes. In code, one would use statements like `from metaflow import Metaflow` or `from metaflow import Flow`/`Run` to access data. For example, listing all flows in the local datastore can be done with: 

```python
from metaflow import Metaflow
flows = Metaflow().flows   # list of Flow objects
print(flows)
```

This client usage is identical to when Metaflow is pointed at a metadata service; by default it will look at the local `.metaflow` directory. As the docs note, *“Metaflow supports a local mode (`.metaflow` directory on your filesystem) and a remote mode.”*【47†L320-L324】. Thus the adapter can simply call `Flow('MyFlow')`, iterate `for run in Flow.runs()`, then use `run.steps()` and `step.tasks()` to collect all needed data. Each `DataArtifact` in a task (accessible via `task.data`) contains metadata and values of that artifact【75†L79-L84】. The Python backend will serialize these objects into JSON for the UI.  

# Mapping Local Data to UI Endpoints  
The existing Metaflow UI frontend expects to fetch runs and metadata via a REST API (the METAFLOW_SERVICE). In standalone mode, the local adapter must expose equivalent endpoints. For example, one would create HTTP routes like `/flows` (listing flow names and IDs), `/flows/{name}/runs` (listing runs), `/flows/{name}/runs/{id}/steps` (steps in a run), and so on. Each endpoint handler uses the client API to fetch the required objects. For instance: 

- **List flows/runs:** Call `Metaflow().flows` to get all flows, or `flow.runs()` for runs of a flow (see above).  
- **Run details:** Use `Run('FlowName/RunID')` to inspect parameters, status, and tags.  
- **Step and task info:** For each run, use `run.steps()` to iterate steps, and `step.tasks()` to iterate tasks. Each task provides artifact values (`task.data.*`) and status.  
- **Logs:** The adapter can read the task’s `stdout` and `stderr` logs from the local datastore and stream them.  

These JSON APIs mirror those of the official UI service. In practice, setting the environment variable `METAFLOW_SERVICE` to `http://localhost:<port>/` (where the adapter runs) makes the React frontend point to this local backend. In the current UI, for example, one typically starts the UI with: 

```
METAFLOW_SERVICE=http://localhost:8083/ npx metaflow-ui
``` 

demonstrating how the UI expects a service URL【73†L342-L346】. In standalone mode, our CLI could set this internally or instruct the user accordingly.  

# Launching the Standalone UI Frontend  
With the local adapter running (serving API routes from the `.metaflow` data), the React frontend (metaflow-ui) can be launched as usual. The developer could use the existing UI build (in development or production mode) and just point it at the local adapter’s URL. In a complete solution, the `metaflow ui` command would start both the Python server and, if desired, launch the frontend (perhaps opening a browser to `http://localhost:3000`). This achieves *“one-command local deployment”* as required【45†L270-L272】. The frontend will then show the DAG, run statuses, logs, etc., in real-time by polling or using WebSockets to our adapter. All data (parameters, artifacts, metrics) comes from the local runs via the adapter, enabling run comparisons and live DAG updates without any external service. 

**References:** The Metaflow docs confirm the use of the client API for local data and the requirement for a backend: for example, *“Metaflow supports a local mode (`.metaflow` directory) and a remote mode”*【47†L320-L324】, and the UI currently *“requires Metaflow Service”*【73†L342-L346】. This standalone backend essentially replaces the service by reading from `.metaflow` using the same API objects (e.g. `Metaflow().flows`, `Flow('Name').runs`【75†L79-L84】). These code-level entry points guide how to implement the local adapter and CLI integration. 

