# Organizing tabular data

The question of managing tabular (e.g. clinical or behavioural) data is a complex one. The main challenges include
1. Lack of a standardized vocabulary for naming variables
2. Asynchrony between tabular and imaging data collection workflows
3. Difficulty in defining criteria for data validation

[BIDS extension proposal (BEP) 36](https://bids.neuroimaging.io/extensions/beps/bep_036.html) is one of the major efforts in this space aimed at providing guidelines on standardized naming and organization of tabular data. Nipoppy will support and promote this standard once merged, and therefore we do not have any strong rules or validations for tabular data management the moment. Having said that, we do have a few recommendations that align with the BIDS direction and can be helpful in general.

## Source (i.e. acquired) data
Similar to imaging data, it is good to separate "data collection" from "data curation" tasks even for the tabular data. This way we don't modify the acquired source data and only create "clean" curated copies. This is especially useful when your study has different naming conventions for your `participant_id`s and/or `visit_id`s for the tabular vs imaging data. The recommended location for putting the "collected/acquired" data dump is {{dpath_src_tabular}} directory.

```{note}
If you do have different naming conventions for the clinical visits vs imaging sessions, then you can establish the correct mapping between those (e.g. `V01` <-> `ses-BL`) in the [manifest](../manifest/index) file.
```

## Demographic variables
For data curation, we begin with writing custom scripts to generate "clean" data files from source data dump. These files will go in the {{dpath_tabular}} directory. Here we usually recommend first creating a `demographics.tsv` file that includes typical demographic variables collected by most studies, such as `date of birth`/`age`, `sex`, `recruitment cohort`, `screening date` etc. One can also think of this file as the basic participant information recorded at a recruitment / screening visit that is static and does not change over time. However, since Nipoppy does not validate any tabular files, you can include multiple visits per participants here if preferred.

### Example demographics TSV file

:::{csv-table}
---
file: ./inserts/example1-demographics.tsv
header-rows: 1
delim: tab
---
:::

## Behavioural and clinical data
For the behavioural or clinical assessments, we create a {{dpath_assessments}} directory and then generate single TSV file (e.g. `assessment_A.tsv`) per assessment/instrument. This file contains separate row per `participant_id` and `visit_id` (or `session_id` if identical). This modularity at the level of assessment is helpful for quality checks and making corrections or updates. This file organization is also **not** validated by Nippopy, so one can come up alternative ways to organize / split clinical assessment information into separate files as preferred.

### Example assessment TSV file

:::{csv-table}
---
file: ./inserts/example1-assessment.tsv
header-rows: 1
delim: tab
---
:::

### Data dictionaries
For each file generated, it is recommended to create data dictionary i.e. `demographics.json`, `assessment_A.json` etc. next to the data file itself (see examples in [BIDS docs](https://bids.neuroimaging.io/getting_started/folders_and_files/metadata/json.html)). Nipoppy or BIDS itself doesn't help with creating "standardized" data dictionaries, but another related project, [Neurobagel](https://neurobagel.org), can help you with it. Neurobagel provides a simple [annotation tool](https://annotate.neurobagel.org) to help generate the data dictionaries with standardized vocabulary (when available) for your variable names. This will allow you to harmonize variable naming across different datasets (e.g. all demographic variables will be mapped to the same term) - which can be super helpful when you want to combine, compare or analyze multiple datasets.


```{note}
The recommendations provided here are work in progress and only meant to help one get started. Nipoppy is contributing to the [BEP36](https://bids.neuroimaging.io/extensions/beps/bep_036.html) and plans to support it going forward.
```
