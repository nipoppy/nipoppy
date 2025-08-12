# Developing a Nipoppy pipeline

This guide explains how to generate and customize a pipeline configuration for use with Nipoppy.

## Creating initial configuration files
Use the `nipoppy pipeline create` command to generate a sample configuration. Nipoppy supports three pipeline types: `bidsification`, `processing`, and `extraction`.

```bash
nipoppy pipeline create \
    --type processing \
    <PIPELINE_DIR>
```

::::{tip}
Optionally, use the `--source-descriptor` flag to initialize the configuration based on a local [Boutiques](https://boutiques.github.io/) descriptor file. See the [Creating a Boutiques descriptor](#creating-a-boutiques-descriptor)
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

::::{note}
`[[NIPOPPY_DPATH_CONTAINERS]]`: is set in the nipoppy config file.

`[[PIPELINE_NAME]]` and `[[PIPELINE_VERSION]]` are set dynamically during execution using the value from the `"NAME"` and `"VERSION"` fields,
respectively.
::::

::::{warning}
If not using a source descriptor, be sure to update the `"NAME"` and `"VERSION"` fields, and the `<OWNER>` placeholder of the `CONTAINER_INFO`'s `URI`. You may need to replace the entire `URI` if the container name does not follow the `<OWNER>/[[PIPELINE_NAME]]:[[PIPELINE_VERSION]]` naming convention.
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


````{admonition} Helpful commands
---

class: dropdown
---

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

````

#### References

- Full schema: <https://github.com/boutiques/boutiques/blob/master/boutiques/schema/descriptor.schema.json/>
- Documentation: <https://boutiques.github.io/doc/>

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

### Processing pipeline specific files

#### `tracker.json`

Defines output tracking paths:

```json
{
    "PATHS": [
        "[[NIPOPPY_BIDS_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]/anat/[[NIPOPPY_BIDS_PARTICIPANT_ID]]_[[NIPOPPY_BIDS_SESSION_ID]]*_example.txt"
    ],
    "PARTICIPANT_SESSION_DIR": "[[NIPOPPY_BIDS_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]"
}
```

::::{note}
The tracked paths are relative to `{{dpath_pipeline_output}}`.

Assuming a participant 001 and session A, the template strings will resolve to:

- `[[NIPOPPY_PARTICIPANT_ID]]`: `001`
- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: `sub-001`
- `[[NIPOPPY_SESSION_ID]]`: `A`
- `[[NIPOPPY_BIDS_SESSION_ID]]`: `ses-A`

::::

#### `pybids_ignore.json`

Defines file patterns to be excluded from the PyBIDS index. For example:

```yaml
[
    "(.*_)*+T2w",  # ignores all T2w images.
    "(.*_)*+FLAIR",  # ignores all FLAIR images.
    ".*/dwi/",  # Skip any file inside a `dwi` folder.
]
```

::::{note}
Patterns are relative to the BIDS root and use Unix-style wildcards (*, ?).
Use this file to exclude temporary files, logs, and other non-BIDS outputs from indexing.
::::

::::{tip}
Optionally, You can set `GENERATE_PYBIDS_DATABASE` to `False`—skipping the database indexing—to accelerate the pipeline launch.
::::

## Uploading to Nipoppy catalog

Nipoppy provides an easy way to upload and install [community-developed pipelines](https://zenodo.org/search?q=metadata.subjects.subject%3A%22Nipoppy%22&l=list&p=1&s=10&sort=bestmatch) via Zenodo.

::::{important}
Before uploading a pipeline to the catalog via the Nipoppy CLI, you must [generate a Zenodo token](https://zenodo.org/account/settings/applications/tokens/new/).
::::

### `zenodo.json` (Optional)

This file is optional. To provide custom metadata for your Zenodo record you must specify it in the `zenodo.json` file. This file is not part of the `config.json` file.

::::{note}
By default, Nipoppy infers the value using the metadata from the user Zenodo account.
::::

```console
nipoppy pipeline upload \
  --password-file <PASSWORD_FILE> \
  <PIPELINE_DIR>
```

:::{note}
To update an existing Zenodo record, use the `--zenodo-id` flag.
:::


```{literalinclude} /../../nipoppy/data/template_pipeline/zenodo.json
---
linenos: True
language: json
---
```
