# Creating a manifest from data directories on disk for a study with different imaging datatypes

In this example, we have a longitudinal study with imaging visits, but not all participants have the same imaging datatypes for all visits.

We do not have a tabular file indicating which datatypes are available for which participants and visits. However, this information can be obtained by looking at the data directories on disk:

:::{literalinclude} ./inserts/example3-file_tree.txt
:::

Here is a script that creates a Nipoppy manifest for the directory structure above:

:::{attention}
The script below was written for Python 3.11 with `pandas` 2.2.3.
It may not work with older/different versions.
:::

:::{literalinclude} ./inserts/example3-generate_manifest.py
:language: python
:linenos: true
:::

Running this script creates a manifest that looks like this:
:::{csv-table}
:file: ./inserts/example3-manifest.tsv
:header-rows: 1
:delim: tab
:::
