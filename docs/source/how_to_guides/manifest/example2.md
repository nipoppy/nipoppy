---
orphan:
---

# Creating a manifest from another tabular file for a longitudinal study with imaging and non-imaging visits

In this example, we have a longitudinal study with both non-imaging and imaging visits. Specifically, non-imaging (neuropsychological) data was collected every year, and imaging data (anatomical only) was collected every two years.

We start with the demographics CSV file `example2-demographics.csv`:

:::{csv-table}
:file: ./inserts/example2-demographics.csv
:header-rows: 1
:delim: ,
:::

This demographics file gives us the following information:
- The study have 2 participants, one female and one male
- Each participant has 3 non-imaging visits (`NEUROPSYCH_{1,2,3}`) and 2 imaging visits (`MRI_{1,2}`)

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
