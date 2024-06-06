# Converting a dataset to BIDS

TODO

## Summary

### Prerequisites

- A Nipoppy dataset with a valid configuration file and an accurate manifest
    - See the [Quickstart guide](../quickstart.md) for instructions on how to set up a new dataset
- Organized (but not BIDS) imaging data in {{dpath_sourcedata}}`/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` directories
    - See <project:organizing_imaging.md>

### Data directories

| Directory | Content description |
|---|---|
| {{dpath_sourcedata}} | **Input** -- {{content_dpath_sourcedata}} |
| {{dpath_bids}} | **Output** -- {{content_dpath_bids}} |

### Commands

- Command-line interface: [`nipoppy bidsify`](<project:../cli_reference/bidsify.md>)
- Python API: {class}`nipoppy.workflows.BidsConversionRunner`

## Running the BIDS conversion

TODO
