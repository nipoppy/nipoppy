# Running processing pipelines

Just like with the BIDS conversion pipelines, Nipoppy uses the {term}`Boutiques framework <Boutiques>` to run image processing pipelines. By default, new Nipoppy datasets (as created with [`nipoppy init`](<project:../cli_reference/init.md>)) are populated with descriptor files and default invocation files for the following processing pipelines:
- [fMRIPrep](https://fmriprep.org/en/stable/), a pipeline for preprocessing anatomical and functional MRI data.
- [MRIQC](https://mriqc.readthedocs.io/en/latest/index.html), a pipeline for automated quality control (QC) metric extraction

```{note}
Although fMRIPrep and MRIQC are both [BIDS Apps](https://bids-apps.neuroimaging.io/about/), Nipoppy can also be used to run pipelines that are not BIDS Apps. Custom pipelines can be added by creating a Boutiques descriptor file and modifying the configuration file accordingly.
```

% TODO link to a page explaining Boutiques and how it works with Nipoppy

## Summary

### Prerequisites

- A Nipoppy dataset with a valid configuration file and an accurate manifest
    - See the [Quickstart guide](../quickstart.md) for instructions on how to set up a new dataset
- Raw imaging data organized according to the {term}`BIDS` standard in the {{dpath_bids}} directory
    - See <project:bids_conversion.md>

```{include} ./inserts/apptainer_stub.md
```

### Data directories

| Directory | Content description |
|---|---|
| {{dpath_bids}} | **Input** -- {{content_dpath_bids}} |
| {{dpath_derivatives}} | **Output** -- {{content_dpath_derivatives}} |

Within the {{dpath_derivatives}} directory, output files for a specific pipeline are organized like this:
```{literalinclude} ./inserts/pipeline_derivatives.txt
---
class: no-copybutton
---
```

### Commands

- Command-line interface: [`nipoppy run`](<project:../cli_reference/run.md>)
- Python API: {class}`nipoppy.workflows.PipelineRunner`

## Running a processing pipeline

### Using the command-line interface

To process all participants and sessions in a dataset, run:
```console
$ nipoppy run \
    --dataset-root <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME>
```
where `<PIPELINE_NAME>` correspond to the pipeline name as specified in the configuration file.

```{note}
If there are multiple versions for the same pipeline in the configuration file, use `--pipeline-version` to specify the desired version. By default, the first version listed for the pipeline will be used.

Similarly, if `--pipeline-step` is not specified, the first step defined in the configuration file will be used.
```

The pipeline can also be run on a single participant and/or session at a time:
```console
$ nipoppy bidsify \
    --dataset-root <DATASET_ROOT> \
    --pipeline <PIPELINE_NAME> \
    --participant <PARTICIPANT_ID> \
    --session <SESSION_ID>
```

```{hint}
The `--simulate` argument will make Nipoppy print out the command to be executed with Boutiques (instead of actually executing it). It can be useful for checking runtime parameters or debugging the invocation file.
```

See the [CLI reference page](<project:../cli_reference/run.md>) for more information on additional optional arguments.

```{note}
Log files for this command will be written to {{dpath_logs}}`/run`
```

### Using the Python API

```python
from nipoppy.workflows import PipelineRunner

# replace by appropriate values
dpath_root = "<DATASET_ROOT>"
pipeline_name = "<PIPELINE_NAME>"

workflow = PipelineRunner(
    dpath_root=dpath_root,
    pipeline_name=pipeline_name,
)
workflow.run()
```

See the API reference for {class}`nipoppy.workflows.PipelineRunner` for more information on optional arguments (they correspond to the ones for the [CLI](<project:../cli_reference/run.md>)).
