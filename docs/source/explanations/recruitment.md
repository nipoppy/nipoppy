# The recruitment file

Often, the participant IDs generated during the data capture/collection stage are not ideal for subsequent data wrangling tasks: they may contain personal information (e.g. names) or special characters (e.g. spaces, dashes, or punctuation) not permitted by data standards such as {term}`BIDS`. If imaging and clinical data collection are handled by separate people, then such studies may also end up with multiple sets of participant IDs, which requires remapping at a later stage.

The Nipoppy recruitment file is an optional TSV file that aims to solve these issues at the earliest (i.e. before the data curation) stage. It maps all sets of participant-related IDs generated during the data collection stage to the `participant_id` column that serves as the primary ID in all subsequent tasks.

The `participant_id` needs to comply with the {term}`BIDS specification <BIDS>`, which only allows alphanumeric characters (i.e. letters and numbers), and it should not include the `sub-` prefix. If any of the sets of participant IDs generated within the study meets these conditions, then that can become the designated `participant_id` column. Otherwise, users need to create a new set that is BIDS-compliant.

```{tip}
- Exclude special characters (e.g. `-`, `_`), spaces and punctuation
- Use zero-padding for numerical labels to ensure correct alphabetical sorting (e.g., `01` and `10` instead of `1` and `10`).
```

This TSV file can also include a `participant_dicom_dir` column listing the relative DICOM directory path relative to `{{dpath_pre_reorg}}` to handle cases where DICOM directory names and participant IDs are not the same (see the [DICOM reorganization guide](<project:../how_to_guides/user_guide/organizing_imaging.md#organizing-raw-imaging-data>) for details). Note that the `participant_dicom_dir` mapping can also be specified in a separate `DICOM_DIR_MAP_FILE` file in cases where this recruitment file is not needed.

For sanity checks, this file can also be used to list the larger cohort of originally recruited participants. This can help avoid possible confusion created by drop-outs or exclusions during the subsequent study stages (i.e. curation, processing, extraction, and analysis).

The recommended location for the `recruitment.tsv` is {{dpath_src_tabular}} directory.

Here is an example recruitment file:

```{csv-table}
---
file: ../../../nipoppy/data/examples/sample_recruitment.tsv
header-rows: 1
delim: tab
---
```

## In the Nipoppy protocol

The Nipoppy protocol considers the `recruitment.tsv` as an optional helper file part of the "data capture" stage. It is typically created *before* the [manifest](./manifest.md) file, which represents the curated view of the recruited participants and their IDs.
