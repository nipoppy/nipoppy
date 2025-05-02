# User Cases

Nipoppy can help several types of users and use cases to help address challenges related to data curation and processing.

## Users

<img alt="comic_panel_1" src="../_static/img/nipoppy_usecases.jpg" width=750px>

The modular design of Nipoppy offers a variety of entry points for Nipoppy adoption suitable for your workflows and analysis.

In general, Nipoppy workflows are designed to be light-weight and for “self-help” - making the data wrangling tasks simpler and often requiring a “human-in-the-loop” process to address research data heterogeneity issues.

Below we list several use case scenarios and their touchpoints with Nipoppy for users to get started.

## Use cases (individual researchers)

### Imaging Data Curation

- Task: Imaging data standardization starting from acquired scans (e.g. DICOMs)
- Starting point: Source imaging data with an expected list of participants
- End Goal: Curate BIDSified dataset and assert data availability in terms of sample sizes and multi-modal data types
- Related technologies and standards:
    - [BIDS](https://bids.neuroimaging.io/) and [BIDSification tools](../user_guide/bids_conversion.md)
- Nipoppy touchpoints:
    - Commands: [reorg](../cli_reference/reorg.rst), [bidsify](../cli_reference/bidsify.rst)
    - Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`invocation.json <Boutiques>`, {term}`curation_status.tsv <Curation status file>`

### Tabular Data Curation (under development)
- Task: Organize raw demographic, clinical, and other tabular data
- Starting point: Source tabular data collected in spreadsheets or other data capture software (e.g. RedCAP)
- End Goal: Assert data availability across data types and link with imaging modalities
- Related technologies and standards:
    - Pandas (Python) or R
- Nipoppy touchpoints:
    - Commands: _under development_
    - Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, demographics.tsv, phenotypic_status.tsv

### Imaging Data Processing (with common neuroimaging pipelines)
- Task: Process BIDSified data to produce derived imaging output
- Starting point: Valid BIDS dataset
- End Goals: Assert availability of processed output.
- Related technologies and standards:
    - Containers ([Apptainer](https://apptainer.org/) / [Docker](https://www.docker.com/))
    - [Boutiques](https://boutiques.github.io/)
    - HPCs (recommended)
- Nipoppy touchpoints:
    - Commands: [run](../cli_reference/run.rst), [track](../cli_reference/track.rst)
    - Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`invocation.json <Boutiques>`, {term}`tracker_config.json <Tracker config file>`, {term}`processing_status.tsv <Processing status file>`

### Imaging Data Processing (with custom neuroimaging pipelines or run-time configuration)
- Task: Process BIDSified data to produce custom derived imaging output
- Starting point: Organized dataset (BIDS or otherwise) required by the custom pipeline
- End Goals: Assert availability of processed output.
- Related technologies and standards:
    - Python
    - [Boutiques](https://boutiques.github.io/)
    - HPCs (recommended)
- Nipoppy touchpoints:
    - Commands: [run](../cli_reference/run.rst), [track](../cli_reference/track.rst)
    - Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`descriptor.json <Boutiques>`, {term}`invocation.json <Boutiques>`, {term}`pybids_ignore.json <Pybids ignore file>`, {term}`tracker_config.json <Tracker config file>`, {term}`processing_status.tsv <Processing status file>`

### Imaging Data Extraction (with neuroimaging pipelines with extractors)
- Task: Extract “analysis-ready” imaging-derived-phenotypes from the processed output
- Starting point: Successful run from a pipeline with extractor support
- End Goals: Generate tabular files and/or data structures ready for statistical analysis
- Related technologies and standards:
    - [Boutiques](https://boutiques.github.io/)
- Nipoppy touchpoints:
    - Commands: [extract](../cli_reference/extract.rst)
    - Files: {term}`manifest.tsv <Manifest file>`, {term}`global_config.json <Global config file>`, {term}`descriptor.json <Boutiques>`, {term}`invocation.json <Boutiques>`, {term}`processing_status.tsv <Processing status file>`


### Use cases (institutes and consortia)

The above use cases target individual researchers and data managers to help adopt best-practices and [FAIR](https://www.go-fair.org/fair-principles/) data workflows. This can significantly improve reproducibility, reuse, and reduce duplication of effort - particularly in the following two canonical data governance setups.

- Centralized Nipoppy adoption of medium and large size datasets in a lab or institute
    - Provides a single ground truth and inventory of collected and processed data
    - Streamlines and avoids duplication of compute heavy processing
    - Keeps provenance of processing configurations

- Distributed Nipoppy adoption by participating sites in a consortium
    - Enables consistent processing across distributed sites
    - Simplifies tracking of data availability and processing provenance
    - Accelerate deployment of a new pipeline and version upgrades
