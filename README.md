# Nipoppy
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8084759.svg)](https://doi.org/10.5281/zenodo.8084759)
[![PyPI - Version](https://img.shields.io/pypi/v/nipoppy)](https://pypi.org/project/nipoppy/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/license/mit)
[![codecov](https://codecov.io/gh/nipoppy/nipoppy/graph/badge.svg?token=SN38ITRO4M)](https://codecov.io/gh/nipoppy/nipoppy)
[![https://github.com/psf/black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)
[![Documentation Status](https://readthedocs.org/projects/nipoppy/badge/?version=latest)](https://nipoppy.readthedocs.io/en/latest/?badge=latest)

<img alt="Nipoppy logo" src="https://raw.githubusercontent.com/nipoppy/nipoppy/refs/heads/main/logo/logo_square.svg" width=100px style="float:right">

Nipoppy is a lightweight framework for standardized organization and processing of neuroimaging-clinical datasets. Its goal is to help users adopt the
[FAIR](https://www.go-fair.org/fair-principles/) principles
and improve the reproducibility of studies.

The framework includes three components:

1. A protocol for data organization, curation and processing, with steps that include the following:
    - **Organization** of raw data, including conversion of raw DICOMs (or NIfTIs) to [BIDS](https://bids.neuroimaging.io/)
    - **Processing** of imaging data with existing or custom pipelines
    - **Tracking** of data availability and processing status
    - **Extraction** of imaging-derived phenotypes (IDPs) for downstream statistical modelling and analysis

    ![Nipoppy protocol](https://raw.githubusercontent.com/nipoppy/nipoppy/main/docs/source/_static/img/nipoppy_protocol.jpg)

2. A specification for dataset organization that extends the [Brain Imaging Data Structure (BIDS) standard](https://bids.neuroimaging.io/) by providing additional guidelines for tabular (e.g., phenotypic) data and imaging derivatives.

    ![Nipoppy specification](https://raw.githubusercontent.com/nipoppy/nipoppy/main/docs/source/_static/img/nipoppy_specification.jpg)

3. A **command-line interface** and **Python package** that provide user-friendly tools for applying the framework. The tools build upon existing technologies such as the [Apptainer container platform](https://apptainer.org/) and the [Boutiques descriptor framework](https://boutiques.github.io/). Several existing containerized pipelines are supported out-of-the-box, and new pipelines can be added easily by the user.
    - We have also developed a [**web dashboard**](https://digest.neurobagel.org) for interactive visualizations of imaging and phenotypic data availability.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://michellewang.github.io/"><img src="https://avatars.githubusercontent.com/u/29051929?v=4?s=100" width="100px;" alt="Michelle Wang"/><br /><sub><b>Michelle Wang</b></sub></a><br /><a href="https://github.com/nipoppy/nipoppy/commits?author=michellewang" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!