```{attention}
This is the **legacy** user guide and may contain information that is out-of-date.
```

# Organizing raw imaging data

To use Nipoppy to convert imaging data to the {term}`BIDS` standard, the data first needs to be organized in a way that Nipoppy can understand and pass to underlying BIDS converters (see <project:bids_conversion.md>). Since different studies typically follow their own methods for raw imaging data organization, this step may require the creation of a custom mapping file or the overriding of some existing methods in the Python API.

## Summary

### Prerequisites

- A Nipoppy dataset with a valid global configuration file and an accurate manifest
    - See the [Quickstart guide](../../overview/quickstart.md) for instructions on how to set up a new dataset
- Raw imaging data in {{dpath_pre_reorg}}
    - See <project:populating.md>

### Data directories

| Directory | Content description |
|---|---|
| {{dpath_pre_reorg}} | **Input** -- {{content_dpath_pre_reorg}} |
| {{dpath_post_reorg}} | **Output** -- {{content_dpath_post_reorg}} |

### Commands

- Command-line interface: [`nipoppy reorg`](<project:../../cli_reference/reorg.rst>)
- Python API: {class}`nipoppy.workflows.DicomReorgWorkflow`

### Workflow

1. Nipoppy will loop over all participants/sessions that *have* data in {{dpath_pre_reorg}} but *do not have* data in {{dpath_post_reorg}} according to the {term}`curation status file`
    - If the curation status file does not exist, it will be automatically generated
    - If there is an existing curation status file but it does not have all the rows in the manifest, new entries will be automatically added to the curation status file
    - The curation status file can also be completely regenerated with [`nipoppy track-curation --regenerate`](../../cli_reference/track_curation.rst)
2. For each participant-session pair:
    1. Files from the {{dpath_pre_reorg}} directory will be "copied" (the default is to create symlinks) to the {{dpath_post_reorg}} directory into a flat list
    2. The curation status file is updated to indicate that this participant-session pair now has data in {{dpath_post_reorg}}

## Configuring the reorganization

By default, Nipoppy expects "participant-first" organization, like the following:
```{literalinclude} ./inserts/default_dicom_reorg-before.txt
```

All files in participant-session subdirectories (and sub-subdirectories, if applicable) will be reorganized under {{dpath_post_reorg}}`/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` (note the addition of BIDS prefixes), creating a flat list of files, like this:
```{literalinclude} ./inserts/default_dicom_reorg-after.txt
```

By default, the output files will be relative symbolic links ("symlinks") to avoid duplication of files.

If `"DICOM_DIR_PARTICIPANT_FIRST"` is set to `"false"` in the {term}`global configuration file <DICOM_DIR_PARTICIPANT_FIRST>`, then Nipoppy will instead expect session-level directories with nested participant-level directories (e.g., {{dpath_pre_reorg}}`/1/01` for the above example).

(dicom-dir-map-example)=
If the raw imaging data are not organized in any of these two structures, a custom tab-separated file can be created to map each unique participant-session pair to a directory path (relative to {{dpath_pre_reorg}}). This path to this mapping file must be specified in the `"DICOM_DIR_MAP_FILE"` in the {term}`global configuration file <DICOM_DIR_MAP_FILE>`. See the {ref}`schema reference <dicom-dir-map-schema>` for more information.

Here is an example file for a dataset that already uses the `ses-` prefix for sessions:

```{csv-table}
---
file: ../../../../nipoppy/data/examples/sample_dicom_dir_map.tsv
header-rows: 1
delim: tab
---
```

````{admonition} Raw content of the example DICOM directory mapping file
---
class: dropdown
---
```{literalinclude} ../../../../nipoppy/data/examples/sample_dicom_dir_map.tsv
---
linenos: True
---
```
````

```{note}
More granular customization can also be achieved for both the input file paths and the output file names, see <project:#customizing-dicom-reorg>.
```

## Running the reorganization

### Using the command-line interface

```console
$ nipoppy reorg --datatset <NIPOPPY_PROJECT_ROOT>
```

See the [CLI reference page](<project:../../cli_reference/reorg.rst>) for more information on optional arguments (e.g., reading DICOM headers to check the image type, and copying files instead of creating symlinks).

```{note}
Log files for this command will be written to {{dpath_logs}}`/dicom_reorg`
```

### Using the Python API

```python
from nipoppy.workflows import DicomReorgWorkflow

dpath_root = "."  # replace by path to dataset root directory
workflow = DicomReorgWorkflow(dpath_root=dpath_root)
workflow.run()
```

See the API reference for {class}`nipoppy.workflows.DicomReorgWorkflow` for more information on optional arguments (they correspond to the ones for the [CLI](<project:../../cli_reference/reorg.rst>)).

(customizing-dicom-reorg)=
#### Customizing input and output file paths

There may be datasets where the raw imaging files are not organized in a participant-session directory. An example of this would a dataset whose raw DICOM files are in archives, like so:
```{literalinclude} ./inserts/custom_dicom_reorg-before.txt
---
class: no-copybutton
---
```

In this case, using a DICOM directory mapping file as described above is not enough, since files from different imaging sessions are in the same directory.

The {class}`nipoppy.workflows.DicomReorgWorkflow` class exposes two functions for finer control of input paths and output filenames:
- {func}`nipoppy.workflows.DicomReorgWorkflow.get_fpaths_to_reorg` can be overridden to map a participant ID and session ID to a list of absolute filepaths to be reorganized
- {func}`nipoppy.workflows.DicomReorgWorkflow.apply_fname_mapping` can be overridden to rename output files
  - Note: output files will still be in the {{dpath_post_reorg}}`/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` directory

Here is an example of custom imaging data reorganization script:
```{literalinclude} ./inserts/custom_dicom_reorg.py
---
language: python
---
```

Running this script on the data shown above will create the following organized files (by default symlinks):
```{literalinclude} ./inserts/custom_dicom_reorg-after.txt
---
class: no-copybutton
---
```

## Next steps

Now that the raw imaging data has been organized in a standardized participant-session structure, it is ready for [BIDS conversion](./bids_conversion.md)!
