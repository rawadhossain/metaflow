from datetime import datetime, timezone
import time

from metaflow import FlowSpec, Parameter, current, retry, step, get_metadata


class MetadataProbeFlow(FlowSpec):
    """
    Reproducible flow for investigating metadata visibility and lifecycle semantics.
    """

    startup_pause_secs = Parameter(
        "startup-pause-secs",
        default=12,
        type=int,
        help="Sleep in start step so polling can begin after run-id is known.",
    )

    branch_count = Parameter(
        "branch-count",
        default=3,
        type=int,
        help="Number of foreach branches to create.",
    )

    branch_sleep_secs = Parameter(
        "branch-sleep-secs",
        default=8,
        type=int,
        help="Sleep duration for each foreach branch.",
    )

    post_join_pause_secs = Parameter(
        "post-join-pause-secs",
        default=8,
        type=int,
        help="Sleep duration in post_join step for in-flight polling windows.",
    )

    enable_retry_probe = Parameter(
        "enable-retry-probe",
        default=True,
        type=bool,
        help="If true, branch 0 fails on first attempt and succeeds on retry.",
    )

    fail_in_step = Parameter(
        "fail-in-step",
        default="none",
        help="One of: none, post_join, end.",
    )

    @step
    def start(self):
        if self.branch_count < 1:
            raise ValueError("--branch-count must be >= 1")
        if self.fail_in_step not in ("none", "post_join", "end"):
            raise ValueError("--fail-in-step must be one of: none, post_join, end")

        self.flow_started_at_utc = datetime.now(timezone.utc).isoformat()
        self.run_id = current.run_id
        self.metadata_provider = get_metadata()
        self.branches = list(range(self.branch_count))

        print("MetadataProbeFlow starting")
        print("run_id=%s" % self.run_id)
        print("metadata=%s" % self.metadata_provider)
        print("branches=%s" % self.branches)
        print("Sleeping %d seconds in start step..." % self.startup_pause_secs)
        time.sleep(self.startup_pause_secs)
        self.next(self.branch, foreach="branches")

    @retry(times=1, minutes_between_retries=0)
    @step
    def branch(self):
        branch_id = self.input
        self.branch_id = branch_id
        self.branch_attempt = current.retry_count
        self.branch_started_at_utc = datetime.now(timezone.utc).isoformat()

        print(
            "branch=%d task_id=%s retry_count=%d"
            % (branch_id, current.task_id, current.retry_count)
        )

        if self.enable_retry_probe and branch_id == 0 and current.retry_count == 0:
            print("Injecting retry probe failure in branch 0 first attempt")
            raise RuntimeError("intentional-retry-probe-failure")

        time.sleep(self.branch_sleep_secs)
        self.branch_payload = {
            "branch_id": branch_id,
            "attempt": current.retry_count,
            "task_id": current.task_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        self.next(self.join)

    @step
    def join(self, inputs):
        inputs_list = list(inputs)
        self.joined_count = len(inputs_list)
        self.branch_payloads = sorted(
            [inp.branch_payload for inp in inputs_list], key=lambda x: x["branch_id"]
        )
        self.next(self.post_join)

    @step
    def post_join(self):
        print("post_join sleeping %d seconds..." % self.post_join_pause_secs)
        time.sleep(self.post_join_pause_secs)
        if self.fail_in_step == "post_join":
            raise RuntimeError("intentional-post-join-failure")
        self.next(self.end)

    @step
    def end(self):
        self.flow_finished_at_utc = datetime.now(timezone.utc).isoformat()
        if self.fail_in_step == "end":
            raise RuntimeError("intentional-end-step-failure")
        print("MetadataProbeFlow completed")
        print("run_id=%s" % current.run_id)
        print("finished_at_utc=%s" % self.flow_finished_at_utc)


if __name__ == "__main__":
    MetadataProbeFlow()