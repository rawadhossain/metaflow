import argparse
import json


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _latest_non_error(snaps):
    for snap in reversed(snaps):
        if "error" not in snap:
            return snap
    return None


def _task_index(snapshot):
    idx = {}
    for step in snapshot.get("steps", []):
        step_id = step["step_id"]
        for task in step.get("tasks", []):
            idx["%s/%s" % (step_id, task["task_id"])] = task
    return idx


def main():
    parser = argparse.ArgumentParser(
        description="Compare final snapshots from local and service metadata runs."
    )
    parser.add_argument("--local-file", required=True)
    parser.add_argument("--service-file", required=True)
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    local = _load(args.local_file)
    service = _load(args.service_file)

    local_last = _latest_non_error(local)
    service_last = _latest_non_error(service)
    if not local_last or not service_last:
        raise RuntimeError("Could not find non-error snapshots in one or both files.")

    lines = []
    lines.append("# Metadata Snapshot Comparison")
    lines.append("")
    lines.append("## Run-Level")
    for key in ("finished", "successful", "finished_at", "end_task_exists"):
        lv = local_last["run"].get(key)
        sv = service_last["run"].get(key)
        marker = "MATCH" if lv == sv else "DIFF"
        lines.append("- %s `%s`: local=%r service=%r" % (marker, key, lv, sv))

    lines.append("")
    lines.append("## Task-Level (final snapshot)")
    local_tasks = _task_index(local_last)
    service_tasks = _task_index(service_last)
    all_keys = sorted(set(local_tasks) | set(service_tasks))
    if not all_keys:
        lines.append("- No tasks found in one or both snapshots.")
    else:
        for key in all_keys:
            lt = local_tasks.get(key)
            st = service_tasks.get(key)
            if lt is None:
                lines.append("- DIFF `%s`: missing in local snapshot" % key)
                continue
            if st is None:
                lines.append("- DIFF `%s`: missing in service snapshot" % key)
                continue

            field_diffs = []
            for f in ("finished", "successful", "finished_at", "current_attempt", "attempt_ok"):
                if lt.get(f) != st.get(f):
                    field_diffs.append("%s local=%r service=%r" % (f, lt.get(f), st.get(f)))
            if field_diffs:
                lines.append("- DIFF `%s`: %s" % (key, "; ".join(field_diffs)))
            else:
                lines.append("- MATCH `%s`" % key)

    result = "\n".join(lines) + "\n"
    print(result)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print("Wrote comparison report to %s" % args.output_file)


if __name__ == "__main__":
    main()
