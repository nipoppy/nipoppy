# IDP specification

Imaging-derived phenotypes (IDPs) are measures produced by extraction pipelines that can be directly used in downstream statistical or machine learning analyses.

The Nipoppy framework recommends that IDP files follow the following specification:
1. File format: tab-separated file (TSV)
2. Index columns:
    1. `participant_id`: participant identifier, without the `sub-` prefix
    2. `session_id`: session identifier, without the `ses-` prefix
    <!-- 3. `long_id` (optional): additional column that may be included for longitudinal analyses (e.g. to denote the longitudinal template used) -->
3. All other column names must be unique
4. An extraction pipeline can produce multiple IDP files
    1. In that case, non-index column names should not be duplicated between the files
5. IDP files must be stored within the {{dpath_pipeline_idp}} directory associated with the relevant upstream processing pipeline

IDP files that comply with the above specification can be used with the {py:class}`nipoppy.NipoppyDataRetriever` API, which can combine multiple IDP files with harmonized phenotypic data into a single {py:class}`pandas.DataFrame` ready for analysis.
