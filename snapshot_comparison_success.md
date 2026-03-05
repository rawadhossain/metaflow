# Metadata Snapshot Comparison

## Run-Level
- MATCH `finished`: local=True service=True
- MATCH `successful`: local=True service=True
- DIFF `finished_at`: local='2026-03-04T14:21:49.008000' service='2026-03-04T14:58:08.219000'
- MATCH `end_task_exists`: local=True service=True

## Task-Level (final snapshot)
- DIFF `branch/2`: missing in service snapshot
- DIFF `branch/3`: finished_at local='2026-03-04T14:21:34.980000' service='2026-03-04T14:57:47.463000'; current_attempt local=0 service=1
- DIFF `branch/4`: finished_at local='2026-03-04T14:21:34.981000' service='2026-03-04T14:57:42.296000'
- DIFF `branch/5`: missing in local snapshot
- DIFF `end/7`: missing in service snapshot
- DIFF `end/8`: missing in local snapshot
- DIFF `join/5`: missing in service snapshot
- DIFF `join/6`: missing in local snapshot
- DIFF `post_join/6`: missing in service snapshot
- DIFF `post_join/7`: missing in local snapshot
- DIFF `start/1`: missing in service snapshot
- DIFF `start/2`: missing in local snapshot
