# Extracting IDPs from pipeline derivatives

Extraction pipelines ingest a subset of processing pipeline outputs into analysis-ready participant- and/or group-level imaging-derived phenotypes (IDPs) useful for particular downstream analysis (e.g., cortical thickness/subcortical volume tables, connectivity matrices).

A processing pipeline can have many downstream extraction pipelines (e.g. volumetric vs vertex-wise or surface measure extractors). Typically, an extractor will depend only on a single processing pipeline, but Nipoppy can support multiple processing pipeline dependencies as well (e.g., in the case of network extractors utilizing both diffusion and functional outputs).

<!-- Another difference between extractor pipelines and processing pipelines is that extractor pipelines are generally tailored for specific downstream analyses, while processing pipelines are more general-purpose. In terms of implementation, extraction pipelines are less likely to be containerized (though we highly encourage it), or they might reuse the container that generated the processed output instead of their own container. -->

Just like with the BIDS conversion and processing pipelines, Nipoppy uses the {term}`Boutiques framework <Boutiques>` to run extraction pipelines.


## Summary

### Prerequisites

- A Nipoppy dataset with a valid global configuration file and an accurate manifest
    - See the [Quickstart guide](../quickstart.md) for instructions on how to set up a new dataset
- Processed imaging data in {{dpath_pipeline_output}} for the relevant processing pipeline(s) that the extractor depends on
    - See <project:processing.md>
- An {term}`imaging bagel file` with completion statuses for the processing pipeline(s) associated with the extraction pipeline.
    - This is obtained by running `nipoppy track` (see <project:tracking.md>)

### Data directories

| Directory | Content description |
|---|---|
| {{dpath_pipeline_output}} | **Input** -- {{content_dpath_pipeline_output}} |
| {{dpath_pipeline_idp}} | **Output** -- {{content_dpath_pipeline_idp}} |

### Commands

- Command-line interface: [`nipoppy extract`](<project:../cli_reference/extract.md>)
- Python API: {class}`nipoppy.workflows.ExtractionRunner`

### Workflow

1. Nipoppy will check the {term}`imaging bagel file` and loop over all participants/sessions that have completed processing for all the pipelines listed in the `PROC_DEPENDENCIES` field.
    - See <project:tracking.md> for more information on how to generate the bagel file
    - Note: an extraction pipeline may be associated with more than one processing pipeline, and the same processing pipeline can have more than one downstream extraction pipeline
2. For each participant-session pair:
    1. The pipeline's invocation will be processed such that template strings related to the participant/session and dataset paths (e.g., `[[NIPOPPY_PARTICIPANT_ID]]`) are replaced by the appropriate values
    2. The pipeline is launched using {term}`Boutiques`, which will be combine the processed invocation with the pipeline's descriptor file to produce and run a command-line expression

## Configuring extraction pipelines

Just like with BIDS pipelines and processing pipelines, pipeline and pipeline step configurations are set in the global configuration file (see [here](./global_config.md) for a more complete guide on the fields in this file).

There are several files in pipeline step configurations that can be further modified to customize pipeline runs:
- `INVOCATION_FILE`: a {term}`JSON` file containing key-value pairs specifying runtime parameters. The keys correspond to entries in the pipeline's descriptor file.

```{note}
By default, pipeline files are stored in {{dpath_pipelines}}`/<PIPELINE_NAME>-<PIPELINE_VERSION>`.
```

```{warning}
Pipeline step configurations also have a `DESCRIPTOR_FILE` field, which points to the {term}`Boutiques` descriptor of a pipeline. Although descriptor files can be modified, in most cases it is not needed and we recommend that less advanced users keep the default.
```

### Customizing pipeline invocations

```{include} ./inserts/boutiques_stub.md
```

(invocation-template-strings)=
{{template_strings_bids_runner}}

## Running an extraction pipeline

### Using the command-line interface

To process all participants and sessions in a dataset (sequentially), run:
```console
$ nipoppy extract \
    <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME>
```
where `<PIPELINE_NAME>` correspond to the pipeline name as specified in the global configuration file.

```{note}
If there are multiple versions for the same pipeline in the global configuration file, use `--pipeline-version` to specify the desired version. By default, the first version listed for the pipeline will be used.

Similarly, if `--pipeline-step` is not specified, the first step defined in the global configuration file will be used.
```

The pipeline can also be run on a single participant and/or session (useful for batching on clusters and testing pipelines/configurations):
```console
$ nipoppy extract \
    <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME> \
    --participant-id <PARTICIPANT_ID> \
    --session-id <SESSION_ID>
```

```{hint}
The `--simulate` argument will make Nipoppy print out the command to be executed with Boutiques (instead of actually executing it). It can be useful for checking runtime parameters or debugging the invocation file.
```

See the [CLI reference page](<project:../cli_reference/extract.md>) for more information on additional optional arguments.

```{note}
Log files for this command will be written to {{dpath_logs}}`/extract`
```

### Using the Python API

```python
from nipoppy.workflows import ExtractionRunner

# replace by appropriate values
dpath_root = "<DATASET_ROOT>"
pipeline_name = "<PIPELINE_NAME>"

workflow = ExtractionRunner(
    dpath_root=dpath_root,
    pipeline_name=pipeline_name,
)
workflow.run()
```

See the API reference for {class}`nipoppy.workflows.ExtractionRunner` for more information on optional arguments (they correspond to the ones for the [CLI](<project:../cli_reference/extract.md>)).

## Next steps

Extracted IDPs are the end-goal of the current Nipoppy framework. There are no next steps after that, though we encourage the use of similar best practices to ensure the reproducibility of any downstream analysis step.
