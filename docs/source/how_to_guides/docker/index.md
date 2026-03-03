# Using Nipoppy with Docker

This guide describes the steps required to run Nipoppy with {term}`Docker`.

By default, Nipoppy will try to use {term}`Apptainer`, but support for {term}`Docker` was added in version [0.4.2](https://github.com/nipoppy/nipoppy/releases/tag/0.4.2).

## Study-level configuration

The following changes need to be made to the `"CONTAINER_CONFIG"` field of the `global_config.json` file:
- `"COMMAND"` should be set to `"docker"` instead of `"apptainer"`
- Any non-Docker argument/option should be removed from `"ARGS"`
    - In particular, the default `global_config.json` uses the `"--cleanenv"` argument, which is specific to Apptainer and needs to be removed if using Docker.
    - Any user-specific bind paths also need to be changed to `--volume` instead of `--bind`. If using Nipoppy 0.4.6 or later, use the new dedicated `"BIND_PATHS"` field instead as it is agnostic to the container platform.

```{literalinclude} ../../../../nipoppy/data/examples/sample_global_config.json
---
linenos: True
language: json
emphasize-lines: 9,11
---
```

## Pipeline-level configuration

Similarly to `global_config.json`, pipeline-specific `config.json` files also have `"CONTAINER_CONFIG"` fields.
They can appear at the top level or inside individual step configurations.
The same changes described above need to be applied to these `"CONTAINER_CONFIG"` fields.
Most commonly, bind paths need to be changed to `--volume` instead of `--bind`.
If using Nipoppy 0.4.6 or later, use the new dedicated `"BIND_PATHS"` field instead as it is agnostic to the container platform.

```{literalinclude} ./fmriprep_config.json
---
linenos: True
language: json
emphasize-lines: 13,15,17,19
---
```
