# Creating a manifest from a wide-form tabular file for a longitudinal study with imaging and non-imaging visits

In this example, we have a longitudinal study with both non-imaging and imaging visits. Specifically, non-imaging (neuropsychological) data was collected every year, and imaging data (anatomical only) was collected every two years.

We start with two CSV files:
- `example2-demographics_neuropsych.csv` contains demographics information and dates for the neuropsych visits
    :::{csv-table}
    :file: ./inserts/example2-demographics_neuropsych.csv
    :header-rows: 1
    :delim: ,
    :::
- `example2-mri.csv` contains dates for the MRI visits
    :::{csv-table}
    :file: ./inserts/example2-mri.csv
    :header-rows: 1
    :delim: ,
    :::

These files give us the following information:
- The study has 3 participants
- Each participant has 3 non-imaging visits and 2 imaging visits

Given that we know that all imaging sessions collected anatomical data only, we have all the information required for the manifest file.
Here is a manifest-generation script that does the job:

:::{attention}
The script below was written for Python 3.11 with `pandas` 2.2.3.
It may not work with older/different versions.
:::

:::{literalinclude} ./inserts/example2-generate_manifest.py
:language: python
:linenos: true
:::

Running this script creates a manifest that looks like this:
:::{csv-table}
:file: ./inserts/example2-manifest.tsv
:header-rows: 1
:delim: tab
:::
