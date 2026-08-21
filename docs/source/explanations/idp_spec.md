# IDP specification

Imaging-derived phenotypes (IDPs) are measures produced by extraction pipelines (most often from processing pipeline output files) that can be directly used in downstream statistical or machine learning analyses.
This page describes the Nipoppy specification for IDPs.
It is meant to help standardize the output of extraction pipelines in the Nipoppy ecosystem and enable compatibility between the Nipoppy Python API and extraction pipeline output.

```{note}
This specification currently only covers tabular measures. It may be extended in the future to support measures that cannot easily be aggregated into a single tabular file.
```

The Nipoppy framework recommends that tabular IDP files follow this specification:
1. The file format should be tab-separated (TSV)
2. The file name should be informative and may contain the name and version of the extraction pipeline and/or the parent processing pipeline(s), e.g. `<parent_pipeline_name>-<parent_pipeline_version>-<measure>.tsv`
3. Index columns:
    1. `participant_id`: participant identifier, without the `sub-` prefix
    2. `session_id`: session identifier, without the `ses-` prefix
    <!-- 3. `long_id` (optional): additional column that may be included for longitudinal analyses (e.g. to denote the longitudinal template used) -->
4. All other column names must be unique
5. An extraction pipeline can produce multiple IDP files. In that case, non-index column names should not be duplicated between the files
6. IDP files must be stored within the {{dpath_pipeline_idp}} directory associated with the relevant upstream processing pipeline
7. It is recommended for IDP files to be accompanied by a JSON data dictionary file describing their columns. The name of the JSON file must be the same as the TSV file, but with a `.json` extension instead of `.tsv`.

IDP files that comply with the above specification can be used with the {class}`nipoppy.NipoppyDataRetriever` API, which can combine multiple IDP files with harmonized phenotypic data into a single {class}`pandas.DataFrame` ready for analysis.
