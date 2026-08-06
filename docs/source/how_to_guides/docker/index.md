# Using Nipoppy with Docker

This guide describes the steps required to run Nipoppy with the {term}`Docker` container engine, for which support was added in version [0.4.2](https://github.com/nipoppy/nipoppy/releases/tag/0.4.2).

## Study-level configuration

The following changes need to be made to the `"CONTAINER_CONFIG"` field of the `global_config.json` file:
- `"COMMAND"` should be set to `"docker"` instead of `"apptainer"`
- Any non-Docker argument/option should be removed from `"ARGS"`
    - In particular, the default `global_config.json` uses the `"--cleanenv"` argument, which is specific to Apptainer and needs to be removed if using Docker.

```{tip}
To avoid having to manually make these changes for every new Nipoppy study, you can set a custom configuration file at {{fpath_user_config}} to be used instead of the default one below.
See {ref}`here <default-config-override>` for more information.
```

```{literalinclude} ../../../../nipoppy/data/examples/sample_global_config.json
---
linenos: True
language: json
emphasize-lines: 9,11
---
```

```{attention}
The `"BIND_PATHS"` field was only added in version 0.4.6.
For older versions of Nipoppy, use the `"ARGS"` with the Docker-specific bind flag `--volume`,
and make sure to specify explicitly the target (destination) path (e.g. `--volume /source:/target` instead of `--volume /source`).
```

## Pipeline-level configuration

Similarly to `global_config.json`, pipeline-specific `config.json` files also have `"CONTAINER_CONFIG"` fields.
They can appear at the top level or inside individual step configurations.
The same changes described above need to be applied to these `"CONTAINER_CONFIG"` fields.

```{literalinclude} ./fmriprep_config.json
---
linenos: True
language: json
---
```
