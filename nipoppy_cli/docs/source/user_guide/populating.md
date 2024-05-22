# Populating an empty dataset

Once an empty Nipoppy dataset has been created, the next step is to populate it with the raw data available in the study.

In general, all data pertaining to the study should be stored together (i.e., under {{dpath_root}}), as that makes it easier to maintain the dataset, link data between modalities, and keep track of the available data.

```{note}
Depending on the study you are working with, there might not be any data to put in some of the directories described below -- that is not an issue. On the other hand, if your study has data that does not seem to fit anywhere, you should still try to store it inside the Nipoppy dataset. You can create additional top-level directories for non-imaging and non-tabular data (in moderation).
```

## Summary

**Prerequisites**
- An empty Nipoppy dataset, as created by [`nipoppy init`](../cli_reference/init.md)
    - See the [Quickstart guide](../quickstart.md) for full instructions on
    initializing a new dataset

**Where to put data**
| Directory | Content description |
|---|---|
| {{dpath_downloads}} | Data archives, web downloads, etc. (imaging and non-imaging data) |
| {{dpath_raw_imaging}} | Arbitrarily organized raw imaging data (DICOMs or NIfTIs) |

## Data archives and web downloads

The {{dpath_downloads}} directory is for storing data archives (e.g., `.zip`, `.tar`, or `.tar.gz` files), or any file downloaded/moved from another location (e.g., spreadsheets for raw tabular data). An example of this would be file dumps downloaded from web portals (e.g., [LONI](https://ida.loni.usc.edu/login.jsp)).

There is no specification for the internal organization inside this directory, though it should be internally consistent. If downloads are made at multiple points in time, files should be labelled with a timestamp (and not overwritten).

```{caution}
If you have imaging data that does not need to be uncompressed/extracted (for example, if the {term}`BIDS` conversion pipeline you plan to use can handle data archives), then it should *not* go in the {{dpath_downloads}} directory. Instead, those files should go directly to the appropriate imaging data directory (see below).
```

## Raw imaging data

The {{dpath_raw_imaging}} directory is for storing raw imaging data. This typically consists of [DICOM](https://en.wikipedia.org/wiki/DICOM) files from scanners, though some analyses might start with files in the NIfTI format instead (e.g., if DICOM-to-NIfTI conversion has already been done and the original DICOMs are not available anymore).

```{attention}
If both DICOMs and NIfTIs are available, we recommend starting over with the DICOMs since they contain more information than NIfTIs for BIDS conversion. If that is not possible, then {{dpath_raw_imaging}}
```

The purpose of the {{dpath_raw_imaging}} directory is for storing **raw data as they are, before any organization/processing is done**, so it is okay (and expected) for the data to be messy or to follow an arbitrary organization (e.g., many subfolder levels). This data should still be in the Nipoppy dataset so that all subsequent steps are documented for reproducibility purposes.

## Next steps

For imaging data, the next step is to [reorganize the data](organization.md) in a way that prepares it for {term}`BIDS` conversion.

<!-- TODO uncomment when tabular page is done
If you have tabular data, we also provide guidelines for wrangling and linking tabular data [here](organization_tabular.md) -->
