# Developing a Nipoppy pipeline

This guide explains how to generate and customize a pipeline configuration for use with Nipoppy.

## Creating initial configuration files
Use the `nipoppy pipeline create` command to generate a sample configuration. Nipoppy supports three pipeline types: `bidsification`, `processing`, and `extraction`.

```bash
nipoppy pipeline create \
    --type processing \
    --source-descriptor $HOME/.cache/boutiques/production/zenodo-7435009.json \
    pipelines/howto
```

::::{tip}
Use the `--source-descriptor` flag to initialize the configuration based on an existing [Boutiques](https://boutiques.github.io/) descriptor.
::::

This will create the following structure:

```console
$ tree ./pipelines/howto
pipelines/howto
├── config.json
├── descriptor.json
├── hpc.json
├── invocation.json
├── pybids_ignore.json
└── tracker.json
```

## Customizing configuration files

### `config.json`

Edit general pipeline metadata and settings.

Example for the [FSL SIENA](https://fsl.fmrib.ox.ac.uk/fsl/docs/#/structural/siena/index) pipeline:

```{literalinclude} data/config.json
---
linenos: True
language: json
emphasize-lines: 2-11
---
```

::::{warning}
If not using a source descriptor, be sure to update the `"NAME"` and `"VERSION"` fields.
::::

### `descriptor.json`
Define how to run your pipeline, including inputs, outputs, and command-line structure, using the [Boutiques](https://boutiques.github.io/) descriptor schema.

::::{note}
You can skip this step if you used a source descriptor.
::::

#### Creating a Boutiques descriptor

A [Boutiques](https://boutiques.github.io/) descriptor is a JSON file that describes:

- the command-line interface of your tool (`"command-line"`),
- required inputs and their types (`"inputs"`),
- outputs and how to find them (`"output-files"`),
- and execution environment (e.g., Docker/Singularity container via `"container-image"`).

Example:

<div style="max-height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 1em;">

```{literalinclude} data/descriptor.json
---
linenos: True
language: json
---
```

</div>

::::{dropdown} Helpful commands

Validating a descriptor:

```bash
bosh validate descriptor.json
```

Generating an invocation template:

```bash
bosh example descriptor.json > invocation.json
```

Simulating a run:

```bash
bosh exec simulate descriptor.json invocation.json
```

::::

#### References

Full schema: <https://github.com/boutiques/boutiques/blob/master/boutiques/schema/descriptor.schema.json/>
Documentation: <https://boutiques.github.io/doc/>


### `invocation.json`
Defines input arguments to the pipeline.

```{literalinclude} data/invocation.json
---
linenos: True
language: json
---
```

::::{tip}
Optionally, you can regenerate the `invocation.json` file to match the descriptor arguments.

```bash
bosh example ./pipelines/howtodescriptor.json > ./pipelines/howto/invocation.json
```

::::

### `tracker.json`

Defines output tracking paths:

```json
{
    "PATHS": [
        "[[NIPOPPY_BIDS_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]/anat/[[NIPOPPY_BIDS_PARTICIPANT_ID]]_[[NIPOPPY_BIDS_SESSION_ID]]*_example.txt"
    ],
    "PARTICIPANT_SESSION_DIR": "[[NIPOPPY_BIDS_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]"
}
```

### `hpc.json` (Optional)

Defines HPC job submission parameters.

```json
{
    "ACCOUNT": "[[HPC_ACCOUNT_NAME]]",
    "TIME": "1:00:00",
    "CORES": "1",
    "MEMORY": "16G",
    "ARRAY_CONCURRENCY_LIMIT": ""
}
```

### `zenodo.json` (Optional)

Customize the Zenodo record metadata. By default, Nipoppy infers the value using the metadata from the user Zenodo account.

```{literalinclude} /../../nipoppy/data/template_pipeline/zenodo.json
---
linenos: True
language: json
---
```
