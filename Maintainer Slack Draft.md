# Slack Draft to Maintainer

Hi! I explored the CLI extensibility issue and prepared a focused proposal plus a small PoC.

I documented:
- non-customizable areas I found in per-flow CLI internals,
- compatibility-focused proposals,
- clarifying questions to confirm scope before expanding the implementation.

Draft docs:
- `CLI Extensibility Proposal.md`
- `CLI Maintainer Questions.md`

PoC currently covers:
- optional lifecycle hooks during `start()` initialization,
- flow-decorator run/resume option extension (`run_options`),
- shared CLI arg serialization utility used by both runtime and CLIArgs singleton.
- hardening for run option registration (normalizes `--foo`/`foo`, better collision checks).

If this direction looks right, I can split follow-ups into smaller PRs (or keep one PR), based on your preference.

Questions I need your input on:
1. Are these lifecycle phases right (`post_datastore`, `post_metadata`, `post_decorators`, `post_start`)?
2. For hook failures, do you prefer fail-fast or warn-and-continue?
3. Is `TL_PLUGINS` acceptable for lifecycle hooks, or do you want a dedicated plugin category?
