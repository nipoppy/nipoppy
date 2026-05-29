# Template strings and other replacement mechanisms

This page explains the multiple string replacement mechanisms used when Nipoppy configuration files are loaded.

## Template string replacement

The global configuration and pipeline configuration files may contain strings or substrings surrounded by double square brackets and starting with the `NIPOPPY_` prefix (e.g., `[[NIPOPPY_PIPELINE_NAME]]`).
These are special *template strings* that are dynamically replaced by Nipoppy at runtime, usually with values that are specific to the dataset and pipeline run (e.g., directory path, pipeline name, participant ID).

### Common template strings

These template strings are available for **all configuration files**:

- `[[NIPOPPY_DPATH_ROOT]]`: path to the root directory of the Nipoppy study
- `[[NIPOPPY_DPATH_BIDS]]`: path to the directory containing raw BIDS data
- `[[NIPOPPY_DPATH_DERIVATIVES]]`: path to the parent derivatives directory
- `[[NIPOPPY_DPATH_PRE_REORG]]`: path to the directory containing imaging data *before* reorganization
- `[[NIPOPPY_DPATH_POST_REORG]]`: path to the directory containing imaging data *after* reorganization
- `[[NIPOPPY_DPATH_CODE]]`: path to the code directory
- `[[NIPOPPY_DPATH_PIPELINES]]`: path to the directory containing pipeline configurations
- `[[NIPOPPY_DPATH_CONTAINERS]]`: path to the directory storing container images
- `[[NIPOPPY_DPATH_LOGS]]`: path to the logs directory
- `[[NIPOPPY_DPATH_TABULAR]]`: path to the directory container curated tabular phenotypic data
- `[[NIPOPPY_FPATH_CONFIG]]`: path to the global configuration file
- `[[NIPOPPY_FPATH_MANIFEST]]`: path to the manifest file
- `[[NIPOPPY_FPATH_CURATION_STATUS]]`: path to the curation status file
- `[[NIPOPPY_FPATH_PROCESSING_STATUS]]`: path to the processing status file
- And other strings of form `[[NIPOPPY_<LAYOUT_PROPERTY>]]`, where `<LAYOUT_PROPERTY>` is a property in the Nipoppy {ref}`dataset layout configuration file <layout-schema>` (all uppercase)

### Pipeline configuration files

These configuration files also have additional utility template strings (note that they are **not** prefixed with `NIPOPPY_`):

- `[[PIPELINE_NAME]]`: name of the pipeline
- `[[PIPELINE_VERSION]]`: version of the pipeline
- `[[STEP_NAME]]`: name of the pipeline step (**only within pipeline step configurations**)

### BIDSification pipeline invocation files

Additional recognized template strings:

- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix
- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix
- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix
- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix

### Processing pipeline invocation files

Additional recognized template strings:

- `[[NIPOPPY_DPATH_PIPELINE_OUTPUT]]`: the output directory for this pipeline, i.e. {{dpath_pipeline_output}}
- `[[NIPOPPY_DPATH_PIPELINE_WORK]]`: the working directory for this pipeline run, which will be a subdirectory of {{dpath_pipeline_work}}
- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix
- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix
- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix
- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix

### Extraction pipeline invocation files

Additional recognized template strings:

- `[[NIPOPPY_DPATH_PIPELINE_IDP]]`: the IDP directory for this pipeline, i.e. {{dpath_pipeline_idp}}
- `[[NIPOPPY_DPATH_PIPELINE_WORK]]`: the working directory for this pipeline run, which will be a subdirectory of {{dpath_pipeline_work}}
- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix
- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix
- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix
- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix

### Tracker configuration files

Additional recognized template strings:

- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix
- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix
- `[[NIPOPPY_DPATH_PIPELINE_OUTPUT]]`: the output directory for this pipeline, i.e. {{dpath_pipeline_output}}
- `[[NIPOPPY_DPATH_PIPELINE_IDP]]`: the IDP directory for this pipeline, i.e. {{dpath_pipeline_idp}}
- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix
- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix

## Optional user-defined substitutions

Substitutions are a mechanism through which users can minimize the number of times the same value (e.g., file or directory path) is copied within the global configuration file.
They can also be used to set specific optional configurations, such as the {term}`HPC` account name.
Substitutions are static and are applied before any template string replacement.
Users can define substitutions using the {term}`SUBSTITUTIONS` field in the global configuration file.
