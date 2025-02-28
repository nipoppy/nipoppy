# Creating a manifest file

This guide shows how to create a manifest file at {{fpath_manifest}}.

A valid manifest file has four columns: `participant_id`, `visit_id`, `session_id` and `datatype`, like so:
```{csv-table}
---
file: ../../../nipoppy/data/examples/sample_manifest.tsv
header-rows: 1
delim: tab
---
```

````{admonition} Raw content of the example manifest file
---
class: dropdown
---
```{literalinclude} ../../../nipoppy/data/examples/sample_manifest.tsv
---
linenos: True
---
```
````

## Columns in the manifest file

```{attention}
There must be only **one row** per unique `participant_id`/`visit_id` combination.
```

### `participant_id`

A unique identifier for a participant in the study. Must be present in every row.
- **Cannot** contain non-alphanumerical characters (spaces, dashes, underscores, etc.)
- **Cannot** have the `sub-` prefix
- Example valid values: `001`, `Control2`
- Example invalid values: `sub-003`, `Control_4`

<!-- TODO `recruitment_id` -->

### `visit_id`

An identifier for a data collection event (imaging or non-imaging). Must be present in every row.

### `session_id`

An identifier for an imaging data collection event. Should be left empty if no imaging data was collected.
- **Cannot** contain non-alphanumerical characters (spaces, dashes, underscores, etc.)
- **Cannot** have the `ses-` prefix
- Example valid values: `1`, `baseline`, `Month12`
- Example invalid values: `ses-1`, `follow-up` `Month_12`

#### Session IDs vs visit IDs

Nipoppy uses the term "session ID" for imaging data, following the convention established by BIDS. The term "visit ID", on the other hand, is used to refer to any data collection event (not necessarily imaging-related), and is more common in clinical contexts. **In most cases, `session_id` and `visit_id` will be identical (or `session_id`s will be a subset of `visit_id`s).** However, having two descriptors becomes particularly useful when imaging and non-imaging assessments do not use the same naming conventions.

### `datatype`

A list of datatypes expected to be in the {term}`BIDS` data. Should be left empty if no imaging data was collected.

Common {term}`MRI` datatypes include:
- `anat`: anatomical MRI
- `dwi`: diffusion MRI
- `func`: functional MRI
- `fmap`: field maps

The full list of valid datatypes is listed in the [BIDS schema](https://github.com/bids-standard/bids-specification/blob/master/src/schema/objects/datatypes.yaml).

## Generating a study's manifest file

<!-- TODO prospective vs retrospective study -->
