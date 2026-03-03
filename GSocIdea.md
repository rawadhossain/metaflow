# GSoC Project Idea:
## Metaflow UI 2.0: Modern Visualization and Standalone Mode

**Difficulty:** Medium/Advanced

**Duration:** 350 hours (Large project)

**Technologies:** TypeScript, React, Python, Metaflow

**Mentors:** Sakari Ikonen

### Description

The current [Metaflow UI](https://github.com/Netflix/metaflow-ui) provides
basic run monitoring but has significant limitations compared to competing
tools like Dagster and Prefect:

- **Requires Metaflow Service** - Cannot view local runs without deploying
  backend infrastructure
- **Static DAG visualization** - No live updates as steps execute
  ([requested](https://github.com/Netflix/metaflow-ui/issues/89))
- **No run comparison** - Cannot diff parameters, artifacts, or metrics
  between runs
- **No dark mode** - A common
  [user request](https://github.com/Netflix/metaflow-ui/issues/157)

Dagster's asset-centric lineage visualization and Prefect's polished
developer experience set user expectations that Metaflow's UI currently
does not meet. This project modernizes the Metaflow UI with standalone
local support, live DAG visualization, run comparison, and improved
developer experience.

### Goals

1. **Standalone local mode** - View runs from the local Metaflow datastore
without requiring Metaflow Service. Single command to launch
(e.g., `metaflow ui`).

2. **Live DAG visualization** - Steps light up in real-time as they execute,
with streaming log output and progress indicators.

3. **Run comparison view** - Side-by-side diff of two runs showing parameter
changes, artifact differences, and metric deltas.

4. **Dark mode and theming** - User-selectable themes with dark mode as a
first-class option.

5. \[Stretch Goal\] **Artifact lineage graph** - Visualize how artifacts flow
through the DAG across steps and runs.

### Deliverables

- Standalone UI that reads from local Metaflow datastore
- Live-updating DAG visualization with step status
- Run comparison/diff interface
- Dark mode theme
- Simplified one-command local deployment
- Documentation and migration guide from existing UI
- Test suite (Cypress)

### Why This Matters

**For users:**
- **Zero-infrastructure local UI** - View and debug local runs without deploying
  any backend services
- **Real-time visibility** - Watch flows execute live instead of refreshing
  static pages
- **Debug faster** - Compare runs side-by-side to identify what changed when
  something breaks
- **Modern developer experience** - Dark mode and polished UX that meets 2025
  expectations

**For the contributor:**
- Work on a full-stack application (React frontend + Python backend)
- Learn real-time data visualization techniques
- Opportunity to improve UX for thousands of Metaflow users

### Skills Required

- TypeScript/React (intermediate/advanced)
- Python (intermediate)
- Data visualization (D3.js or similar)
- Understanding of Metaflow's datastore structure

### Links

- [Metaflow UI Repository](https://github.com/Netflix/metaflow-ui)
- [Metaflow UI Open Issues](https://github.com/Netflix/metaflow-ui/issues)
- [Metaflow Client API](https://docs.metaflow.org/api/client)
- [Dagster UI](https://dagster.io/) (reference for asset lineage)
- [Metaflow Documentation](https://docs.metaflow.org)
