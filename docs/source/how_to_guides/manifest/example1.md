---
orphan:
---

# Creating a manifest from another tabular file for a cross-sectional study

In this example, we have a cross-sectional study where not all participants have the same MRI modalities (datatypes).

The CSV file `example1-participants.csv` (shown below) indicates whether participants have diffusion or functional data. All participants have anatomical data.

:::{csv-table}
:file: ./inserts/example1-participants.csv
:header-rows: 1
:delim: ,
:::

Here is a script that creates a Nipoppy manifest from the above file:

:::{attention}
The script below was written for Python 3.11 with `pandas` 2.2.3.
It may not work with older/different versions.
:::

:::{literalinclude} ./inserts/example1-generate_manifest.py
:language: python
:linenos: true
:::

Running this script creates a manifest that looks like this:
:::{csv-table}
:file: ./inserts/example1-manifest.tsv
:header-rows: 1
:delim: tab
:::
