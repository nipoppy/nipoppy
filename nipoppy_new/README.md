# Nipoppy

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8084759.svg)](https://doi.org/10.5281/zenodo.8084759)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/license/mit)
[![https://github.com/psf/black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)

Nipoppy is a lightweight framework for standardized organization and processing of neuroimaging-clinical datasets. It is designed to help users do the following:

- **Curate and organize** data into a standard directory structure that extends the {term}`Brain imaging data structure <BIDS>`
- **Run** data processing pipelines in a semi-automated and reproducible way
- **Track** the availability (including processing status, if applicable) of (raw and derived) imaging and non-imaging data
- **Extract** imaging features from {term}`MRI` derivatives data for downstream analysis

Nipoppy is very flexible, leveraging the {term}`Boutiques` framework for the execution of image processing pipelines and {term}`BIDS` conversion software. Several existing containerized pipelines are supported out-of-the-box, and new pipelines can be added easily by the user.

% TODO add Quickstart page (?)
To get started, see the [Installation instructions](#installation-instructions).
