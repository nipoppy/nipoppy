# Converting a dataset to BIDS

Organizing imaging data following the {term}`Brain Imaging Data Structure <BIDS>` standard can greatly facilitate downstream processing and sharing of data. However, BIDS conversion can be a tricky process, especially for retrospective and/or messy datasets. Some manual work and trial-and-error process is usually needed to create an accurate configuration file to map the raw DICOMs (or NIfTIs) to valid BIDS paths.

Nipoppy uses the {term}`Boutiques framework <Boutiques>` to run BIDS conversion pipelines. By default, new Nipoppy datasets (as created with [`nipoppy init`](<project:../cli_reference/init.md>)) are populated with descriptor files and default invocation files for the following BIDS converters:
- [dcm2bids](https://unfmontreal.github.io/Dcm2Bids/latest), a user-friendly DICOM converter that is configured with a {term}`JSON` file
- [HeuDiConv](https://heudiconv.readthedocs.io/en/latest/), a flexible DICOM converter that is configured with a heuristic Python file

## Summary

### Prerequisites

- A Nipoppy dataset with a valid configuration file and an accurate manifest
    - See the [Quickstart guide](../quickstart.md) for instructions on how to set up a new dataset
- Organized (but not BIDS) imaging data in {{dpath_sourcedata}}`/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` directories
    - See <project:organizing_imaging.md>

```{include} ./inserts/apptainer_stub.md
```

### Data directories

| Directory | Content description |
|---|---|
| {{dpath_sourcedata}} | **Input** -- {{content_dpath_sourcedata}} |
| {{dpath_bids}} | **Output** -- {{content_dpath_bids}} |

### Commands

- Command-line interface: [`nipoppy bidsify`](<project:../cli_reference/bidsify.md>)
- Python API: {class}`nipoppy.workflows.BidsConversionRunner`

### Workflow

1. Nipoppy will loop over all participants/sessions that *have* data in {{dpath_sourcedata}} but *do not have* BIDS data in {{dpath_bids}} according to the {term}`doughnut file`
    - An existing, out-of-date doughnut file can be updated with [`nipoppy doughnut --regenerate`](../cli_reference/doughnut.md)
2. For each participant-session pair:
    1. The pipeline's invocation will be processed such that template strings related to the participant/session and dataset paths are replaced by the appropriate values
    2. The pipeline is launched using {term}`Boutiques`, which will be combine the processed invocation with the pipeline's descriptor file to produce and run a command-line expression
    3. The doughnut file is updated to indicate that this participant-session pair now has BIDS data

## Configuring the BIDS conversion

Most BIDS conversion tools are designed to be run in steps, with some manual work expected between steps to create/edit a configuration file. The default configuration splits BIDS conversion pipelines into the following steps:
* [`dcm2bids`](https://unfmontreal.github.io/Dcm2Bids/latest)
    * Step `prepare`: run [`dcm2bids_helper`](https://unfmontreal.github.io/Dcm2Bids/3.1.1/tutorial/first-steps/#dcm2bids_helper-command), which will convert DICOM files to NIfTI files with JSON sidecars and store them in a temporary directory
        * The JSON configuration file is expected to be created based on information in the sidecars
    * Step `convert`: run the actual conversion using the configuration file
* [`heudiconv`](https://heudiconv.readthedocs.io/en/latest/)
    * Step `prepare`: extract information from DICOM headers that can be used to write/test the heuristic file
    * Step `convert`: run the actual conversion

```{note}
These step names `prepare` and `convert` are a Nipoppy convention based on the general BIDS conversion process. The BIDS conversion tools themselves do not use these names.
```

### Customizing BIDS pipeline invocations

```{include} ./inserts/boutiques_stub.md
```

{{template_strings_bids_runner}}

## Running the BIDS conversion

### Using the command-line interface

To convert all participants and sessions in a dataset, run:
```console
$ nipoppy bidsify \
    --dataset-root <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME> \
    --pipeline-step <PIPELINE_STEP_NAME>
```
where `<PIPELINE_NAME>` and `<PIPELINE_STEP_NAME>` correspond to the pipeline name and the step name as specified in the configuration file.

```{note}
If `--pipeline-step` is not specified, the first step defined in the configuration file will be used.
```

The BIDS conversion can also be run on a single participant and/or session at a time:
```console
$ nipoppy bidsify \
    --dataset-root <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME> \
    --pipeline-step <PIPELINE_STEP_NAME> \
    --participant <PARTICIPANT_ID> \
    --session <SESSION_ID>
```

```{hint}
The `--simulate` argument will make Nipoppy print out the command to be executed with Boutiques (instead of actually executing it). It can be useful for checking runtime parameters or debugging the invocation file.
```

See the [CLI reference page](<project:../cli_reference/bidsify.md>) for more information on additional optional arguments.

```{note}
Log files for this command will be written to {{dpath_logs}}`/bids_conversion`
```

### Using the Python API

```python
from nipoppy.workflows import BidsConversionRunner

# replace by appropriate values
dpath_root = "<DATASET_ROOT>"
pipeline_name = "<PIPELINE_NAME>"
pipeline_step = "<PIPELINE_STEP>"

workflow = BidsConversionRunner(
    dpath_root=dpath_root,
    pipeline_name=pipeline_name,
    pipeline_step=pipeline_step,
)
workflow.run()
```

See the API reference for {class}`nipoppy.workflows.BidsConversionRunner` for more information on optional arguments (they correspond to the ones for the [CLI](<project:../cli_reference/reorg.md>)).

## Next steps

Now that the imaging data is in BIDS, it is time to [run image processing pipelines](processing.md) on it!
