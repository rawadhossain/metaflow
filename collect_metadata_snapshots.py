import argparse
import json
import time
from datetime import datetime, timezone

from metaflow import Run
from metaflow.client import metadata, namespace


def _iso(dt):
    return None if dt is None else dt.isoformat()


def _collect_snapshot(flow_name, run_id):
    run = Run("%s/%s" % (flow_name, run_id), _namespace_check=False)

    steps = []
    for step in run:
        step_entry = {
            "step_id": step.id,
            "finished_at": _iso(step.finished_at),
            "tasks": [],
        }
        for task in step:
            md = task.metadata_dict
            step_entry["tasks"].append(
                {
                    "task_id": task.id,
                    "current_attempt": task.current_attempt,
                    "successful": task.successful,
                    "finished": task.finished,
                    "finished_at": _iso(task.finished_at),
                    "attempt": md.get("attempt"),
                    "attempt_ok": md.get("attempt_ok"),
                    "origin_run_id": md.get("origin-run-id"),
                    "origin_task_id": md.get("origin-task-id"),
                }
            )
        step_entry["tasks"] = sorted(step_entry["tasks"], key=lambda t: t["task_id"])
        steps.append(step_entry)

    steps = sorted(steps, key=lambda s: s["step_id"])
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "flow_name": flow_name,
        "run_id": str(run_id),
        "run": {
            "successful": run.successful,
            "finished": run.finished,
            "finished_at": _iso(run.finished_at),
            "end_task_exists": run.end_task is not None,
        },
        "steps": steps,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Poll Metaflow client state and write structured run snapshots."
    )
    parser.add_argument("--flow-name", default="MetadataProbeFlow")
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--metadata",
        required=True,
        help="Metadata selector, for example local@. or service@http://127.0.0.1:8080",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help="Namespace value; use 'none' for global namespace. Default: none",
    )
    parser.add_argument("--interval-secs", type=float, default=2.0)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    metadata(args.metadata)
    if args.namespace is None or str(args.namespace).lower() == "none":
        namespace(None)
    else:
        namespace(args.namespace)

    snapshots = []
    print("Collecting snapshots for %s/%s" % (args.flow_name, args.run_id))
    print("metadata=%s interval=%.1fs samples=%d" % (args.metadata, args.interval_secs, args.samples))
    print("output_file=%s" % args.output_file)

    for i in range(args.samples):
        try:
            snap = _collect_snapshot(args.flow_name, args.run_id)
            snapshots.append(snap)
            print(
                "[%03d] %s run.finished=%s run.successful=%s steps=%d"
                % (
                    i + 1,
                    snap["captured_at_utc"],
                    snap["run"]["finished"],
                    snap["run"]["successful"],
                    len(snap["steps"]),
                )
            )
        except Exception as e:
            snapshots.append(
                {
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                    "flow_name": args.flow_name,
                    "run_id": str(args.run_id),
                    "error": str(e),
                }
            )
            print("[%03d] error: %s" % (i + 1, e))
        if i < args.samples - 1:
            time.sleep(args.interval_secs)

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(snapshots, f, indent=2, sort_keys=True)
    print("Wrote %d snapshots to %s" % (len(snapshots), args.output_file))


if __name__ == "__main__":
    main()
