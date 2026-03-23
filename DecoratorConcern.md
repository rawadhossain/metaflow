## Decorator-Based Run/Resume Option Extension
### Concern #1 
This line :

```
existing_params=set(
p.name.lower()forpingetattr(cmd,"__click_params__", [])ifp.name
)
```

### Problem

 __click_params__ contains Option objects, but .name is not always populated. Does'nt Click actually stores the option name differently? 

---

## Concern #2 (Potential)

You do:

```
cmd=click.option("--"+option,**option_kwargs)(cmd)
```
Doesn't Click expects decorator stacking before command registration? If add_run_decorator_options() is applied after Click command creation, the option won't register. right? 
Shouldnt decorator be used like this?:

```
@add_run_decorator_options
@click.command()
def run(...):
```

If applied later, it may not work

# Architectural Concern

Currently:

```
run_options= {
"experiment": {...}
}
```

This assumes option names **without the `--` prefix**.

But nothing enforces that.

Someone could write:

```
run_options= {
"--experiment": {...}
}
```

Which would create:

```
----experiment
```

Better to enforce normalization:

```
option=option.lstrip("-")
```

before constructing the CLI flag. im not sure if normalization practice is used int he codebase, if not probably not a good idea to enforce it, better skip it.