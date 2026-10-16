# Nipoppy

[![Discord](https://dcbadge.limes.pink/api/server/https://discord.gg/2VMKFRpjkm?style=flat)](https://discord.gg/2VMKFRpjkm)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8084759.svg)](https://doi.org/10.5281/zenodo.8084759)
[![Preprint](https://img.shields.io/badge/preprint-10.64898%2F2026.05.18.723593-B31B1B)](https://doi.org/10.64898/2026.05.18.723593)
[![PyPI - Version](https://img.shields.io/pypi/v/nipoppy)](https://pypi.org/project/nipoppy/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/license/mit)
[![codecov](https://codecov.io/gh/nipoppy/nipoppy/graph/badge.svg?token=SN38ITRO4M)](https://codecov.io/gh/nipoppy/nipoppy)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)
[![Documentation Status](https://readthedocs.org/projects/nipoppy/badge/?version=latest)](https://nipoppy.readthedocs.io/en/latest/?badge=latest)
[![All Contributors](https://img.shields.io/github/all-contributors/nipoppy/nipoppy?color=ee8449)](docs/source/other/team.md#contributors)

<img alt="Nipoppy logo" src="https://raw.githubusercontent.com/nipoppy/nipoppy/refs/heads/main/logo/logo_square.svg" width=100px style="float:right">

Nipoppy is a lightweight framework for standardized organization and processing of neuroimaging-clinical data. Its goal is to help users adopt the
[FAIR](https://www.go-fair.org/fair-principles/) principles
and improve the reproducibility of studies.

The framework includes three components:

1. A protocol for data organization, curation and processing, with steps that include the following:
    - **Organization** of raw data, including conversion of raw DICOMs (or NIfTIs) to [BIDS](https://bids.neuroimaging.io/)
    - **Processing** of imaging data with existing or custom pipelines
    - **Tracking** of data availability and processing status
    - **Extraction** of imaging-derived phenotypes (IDPs) for downstream statistical modelling and analysis

    ![Nipoppy protocol](https://raw.githubusercontent.com/nipoppy/nipoppy/main/docs/source/_static/img/nipoppy_protocol.jpg)

2. A specification for study organization that extends the [Brain Imaging Data Structure (BIDS) standard](https://bids.neuroimaging.io/) by providing additional guidelines for tabular (e.g., phenotypic) data and imaging derivatives.

    ![Nipoppy specification](https://raw.githubusercontent.com/nipoppy/nipoppy/main/docs/source/_static/img/nipoppy_specification.jpg)

3. A **command-line interface** and **Python package** that provide user-friendly tools for applying the framework. The tools build upon existing technologies such as the [Apptainer container platform](https://apptainer.org/) and the [Boutiques descriptor framework](https://boutiques.github.io/). Several existing containerized pipelines are supported out-of-the-box, and new pipelines can be added easily by the user.
    - We have also developed a [**web dashboard**](https://digest.neurobagel.org) for interactive visualizations of imaging and phenotypic data availability.

## Citation

If you use Nipoppy in your research, please cite our preprint:

> Nikhil Bhagwat, Michelle Wang, Mathieu Dugré, Julia-Katharina Pfarr, Alyssa Dai, Sebastian Urchs, Brent McPherson, Rémi Gau, Eva M. van Heese, Emile d’Angremont, Max A. Laansma, Shweta Prasad, Jacob Sanz-Robinson, Mohammad Torabi, Arman Jahanpour, Matthew Danyluik, Alice Joubert, Austin Macdonald, Lea Waller, Ashley Stewart, Matthieu Joulot, Erin Dickie, Gabriel A. Devenyi, Sylvain Bouix, Steffen Bollmann, Neda Jahanshad, Paul M. Thompson, Ninon Burgos, M. Mallar Chakravarty, Yaroslav O. Halchenko, Ysbrand D. van der Werf, and Jean-Baptiste Poline (2026). Nipoppy: A framework for standardizing neuroimaging studies to facilitate international derived-data sharing. *bioRxiv*. [https://doi.org/10.64898/2026.05.18.723593](https://doi.org/10.64898/2026.05.18.723593)

<details>
<summary>BibTeX</summary>

```bibtex
@article{Bhagwat2026Nipoppy,
  title = {Nipoppy: A framework for standardizing neuroimaging studies to facilitate international derived-data sharing},
  author = {Bhagwat, Nikhil and Wang, Michelle and Dugr{\'e}, Mathieu and Pfarr, Julia-Katharina and Dai, Alyssa and Urchs, Sebastian and McPherson, Brent and Gau, R{\'e}mi and van Heese, Eva M. and d’Angremont, Emile and Laansma, Max A. and Prasad, Shweta and Sanz-Robinson, Jacob and Torabi, Mohammad and Jahanpour, Arman and Danyluik, Matthew and Joubert, Alice and Macdonald, Austin and Waller, Lea and Stewart, Ashley and Joulot, Matthieu and Dickie, Erin and Devenyi, Gabriel A. and Bouix, Sylvain and Bollmann, Steffen and Jahanshad, Neda and Thompson, Paul M. and Burgos, Ninon and Chakravarty, {M. Mallar} and Halchenko, Yaroslav O. and van der Werf, Ysbrand D. and Poline, Jean-Baptiste},
  publisher = {openRxiv},
  year = {2026},
  month = {May},
  doi = {10.64898/2026.05.18.723593},
  url = {https://doi.org/10.64898/2026.05.18.723593}
}
```
</details>

To cite a specific software release, see our [Zenodo record](https://doi.org/10.5281/zenodo.8084759).
