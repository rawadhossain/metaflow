## Issue Title: Decorator lifecycle hooks and common patterns 
## Issue Description:
Metaflow decorators have strict lifecycle hooks, but they do not impose guarantees on order between the execution of decorators. This means that any cross-reliance on hooks executing between decorators is unreliable, e.g. there is no guarantee that `step_init` of decorator A has executed before `step_init` of decorator B every time, therefore B can not depend on A during the same lifecycle stage.

There are also some commonly occurring patterns around `runtime_step_cli` and `task_pre_step` that could be abstracted away.

## Goals
* Explore existing lifecycle hooks and determine if new ones should be added, or existing ones modified due to common patterns.
* Propose changes if any, with technical details and backwards compatibility as a first priority.
  
  * The way hooks are executed in order to achieve dependable ordering, if possible.
  * Abstractions for common patterns
  * Possible other findings

## Instructions
This issue is meant to be a venue for asking further questions on the topic. Implementation details and proposals are to be kept separate.

When you have met the goals of the issue, it is time to show and tell. You can do this for example with your own fork with an **issue** or **pull request** and messaging a mentor on Slack with a link.

