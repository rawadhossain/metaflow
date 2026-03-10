# 1️⃣ The Biggest Technical Concern: Where to Sort Decorators

The plan says:

> sort decorators in `task.py` and `runtime.py`
> 

That is **not ideal**.

If you sort there, you risk:

- duplicated sorting logic
- inconsistent ordering between different lifecycle calls
- bugs if a new hook site is added later

Instead, shouldn't sorting  happen **once when the decorator list is finalized**.

In Metaflow this usually happens when decorators are attached to the step.

Conceptually:

```
step.decorators
```

is constructed in:

```
decorators.py
_base_step_decorator()
```

So a better place to sort is **right after decorators are collected**.

Example:

```
decorators=sorted(
decorators,
key=lambdad: (getattr(d,"ORDER_PRIORITY",0),original_index)
)
```

Then everywhere else just uses the already-sorted list.

So adjust Phase 1 to:

> Sorting should happen when the decorator list is finalized, not at every hook call site.
> 

---

# 2️⃣ ORDER_PRIORITY Is Good — But Be Careful With Default Behavior

The current proposal is:

```
ORDER_PRIORITY=0
```

This is good because:

- zero breaking change
- preserves current ordering

But **be careful about one thing**:

Source order must still dominate when priorities match.

So sorting should be:

```
(priority,original_index)
```

not just priority.

Example implementation:

```
decorators=sorted(
enumerate(decorators),
key=lambdax: (getattr(x[1],"ORDER_PRIORITY",0),x[0])
)
decorators= [dfor_,dindecorators]
```

Does it guarantees **stable source order**?

----
The concerns may not be fully correct, i maybe worng, so dont forcefully make changes I say. Make your judgement.
The original issue says: "The way hooks are executed in order to achieve dependable ordering, if possible. Abstractions for common patterns. Possible other findings" so I want these to be resolved.