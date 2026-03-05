# Metadata Snapshot Comparison

## Run-Level
- MATCH `finished`: local=False service=False
- MATCH `successful`: local=False service=False
- MATCH `finished_at`: local=None service=None
- MATCH `end_task_exists`: local=False service=False

## Task-Level (final snapshot)
- DIFF `branch/11`: missing in local snapshot
- DIFF `branch/12`: missing in local snapshot
- DIFF `branch/13`: missing in local snapshot
- DIFF `branch/2`: missing in service snapshot
- DIFF `branch/3`: missing in service snapshot
- DIFF `branch/4`: missing in service snapshot
- DIFF `join/14`: missing in local snapshot
- DIFF `join/5`: missing in service snapshot
- DIFF `post_join/15`: missing in local snapshot
- DIFF `post_join/6`: missing in service snapshot
- DIFF `start/1`: missing in service snapshot
- DIFF `start/10`: missing in local snapshot
