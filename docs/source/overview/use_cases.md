# Use cases

Nipoppy can help several types of users and use cases to help address challenges related to data curation and processing.

## Users

![image](../_static/img/nipoppy_usecases.jpg)

The modular design of Nipoppy offers a variety of entry points for Nipoppy adoption suitable for your workflows and analysis.

In general, Nipoppy workflows are designed to be light-weight and for “self-help” - to simplify common data wrangling tasks.

Below we list several use case scenarios and their touchpoints with Nipoppy for users to get started.

## Use cases for individual researchers

| Task | Starting point | End goal | Related tech and standards | Nipoppy touchpoints |
|:-------|:------------------------------------------------------------------------|:--|:--|:--|
|**Imaging Data Curation** |
| Imaging data standardization starting from acquired scans (e.g. DICOMs) | Source imaging data with an expected list of participants | Curate BIDSified dataset and assert multimodal data availability | [BIDS](https://bids.neuroimaging.io/) and [BIDSification tools](../how_to_guides/user_guide/bids_conversion.md) | Commands: [reorg](../cli_reference/reorg.rst), [bidsify](../cli_reference/bidsify.rst) <br> Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`invocation.json <Boutiques>`, {term}`curation_status.tsv <Curation status file>` |
| **Tabular Data Curation** (_under development_)||||
|Organize raw demographic, clinical, and other tabular data | Source tabular data collected in spreadsheets or other data capture software (e.g. RedCAP) | Assert data availability across data types and link with imaging modalities | Pandas (Python) or R | Commands: (_under development_) <br> Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, demographics.tsv, phenotypic_status.tsv |
| **Imaging Data Processing** (_with common pipelines_)||||
|Process BIDSified data to produce derived imaging output| Valid BIDS dataset | Assert availability of processed output |[Apptainer](https://apptainer.org/) / [Docker](https://www.docker.com/) <br> [Boutiques](https://boutiques.github.io/) <br> HPCs (recommended) | Commands: [run](../cli_reference/run.rst), [track](../cli_reference/track.rst) <br> Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`invocation.json <Boutiques>`, {term}`tracker_config.json <Tracker config file>`, {term}`processing_status.tsv <Processing status file>`
| **Imaging Data Processing** (_with custom pipelines_)| |||
|Process BIDSified data to produce custom derived imaging output | Organized dataset (BIDS or otherwise) required by the custom pipeline | Assert availability of processed output | [Apptainer](https://apptainer.org/) / [Docker](https://www.docker.com/) <br> [Boutiques](https://boutiques.github.io/) <br> HPCs (recommended) | Commands: [run](../cli_reference/run.rst), [track](../cli_reference/track.rst) <br> Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`descriptor.json <Boutiques>`, {term}`invocation.json <Boutiques>`, {term}`tracker_config.json <Tracker config file>`, {term}`processing_status.tsv <Processing status file>`|
| **Imaging Data Extraction** ||||
|Extract “analysis-ready” imaging-derived-phenotypes from the processed output | Successful run from a pipeline with extractor support | Generate tabular files and/or data structures ready for statistical analysis | [Boutiques](https://boutiques.github.io/) | Commands: [extract](../cli_reference/extract.rst) <br> Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`descriptor.json <Boutiques>`, {term}`invocation.json <Boutiques>`, {term}`processing_status.tsv <Processing status file>` |

## Long-term sustainable benefits for institutes and consortia

The above use cases target individual researchers and data managers to help adopt best-practices and [FAIR](https://www.go-fair.org/fair-principles/) data workflows. This can significantly improve reproducibility, reuse, and reduce duplication of effort - particularly in the following two canonical data governance setups.

- Centralized Nipoppy adoption of medium and large size datasets in a lab or institute
    - Provides a **single ground truth** and inventory of collected and processed data
    - Streamlines and **avoids duplication** of compute heavy processing
    - Keeps **provenance of processing** configurations

- Distributed Nipoppy adoption by participating sites in a consortium
    - Enables **consistent processing** across distributed sites
    - Simplifies **tracking of data availability** and processing provenance
    - **Accelerate deployment** of a new pipeline and version upgrades
