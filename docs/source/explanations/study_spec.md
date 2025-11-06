# Study specification

Nipoppy provides a specification (i.e. directory layout) for dataset organization that extends the [Brain Imaging Data Structure (BIDS) standard](https://bids.neuroimaging.io/). One can think of this as a "standard" for organizing data generated during a lifecycle of a study which may include sourcedata (e.g. DICOMs), tabular data (e.g., phenotypic assessments), and imaging derivatives (e.g. fMRIPrep output), in addition to the raw BIDS data. A study-level standardized directory layout simplifies curation and processing tasks as well as tracking of outputs. Additionally, the layout consists of directories to store pipeline specifications and custom code used for data processing and wrangling tasks. The complete layout configuration details are provided [here](../schemas/index.rst).

There are on-going efforts to merge this specification as a `study`-level dataset type into the BIDS standard.

The directory tree shown below is generated automatically upon dataset initialization (see [nipoppy init](../how_to_guides/init/index.md)).

![Nipoppy specification](../_static/img/nipoppy_specification.jpg)
