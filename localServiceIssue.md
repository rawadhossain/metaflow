## Issue Title: Compare differences in local metadata vs. metadata service #1
### Issue Description: 
When running Metaflow with local metadata, a bunch of files are persisted on disk. There might exist discrepancies in data that is recorded when relying on local metadata compared to when using a remote metadata service.

For example, can both implementations reliably

* determine when a run has finished
* by polling or other means, track when a run, step, or task has started. What are the data points required for this?
* by polling or other means, track when a run, step or task has failed. What are the data points for this?

The findings in this might also lend towards solving issue 2293

## Goals
* Explore the differences between data recorded with local metadata, and the metadata service.
* Report any severe differences between the two, if any exist.
* Propose changes if needed.

## Instructions
This issue is meant to be a venue for asking further questions on the topic. Implementation details and proposals are to be kept separate.

When you have met the goals of the issue, it is time to show and tell. You can do this for example with your own fork with an **issue** or **pull request** and messaging a mentor on Slack with a link.