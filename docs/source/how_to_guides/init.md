# Initializing a new dataset

This guide shows how to initialize a new Nipoppy dataset.

We cover two possible starting scenarios:
1. [Source imaging data **is not** in {term}`BIDS`](#starting-with-non-bids-data)
2. [Source imaging data **is** in {term}`BIDS`](#starting-with-bids-data)

In both cases, the command to create the dataset is [`nipoppy init`](../cli_reference/init).

## Starting with non-BIDS data

If the study's imaging data consists of DICOM files or NIfTI files that are not yet in BIDS, you will first need to create an empty Nipoppy dataset:

```console
$ nipoppy init --dataset <PATH_TO_NEW_DATASET>
```

This will create the directory tree and copy an [example manifest](https://github.com/nipoppy/nipoppy/blob/main/nipoppy/data/examples/sample_manifest.tsv) and an [example global configuration file](https://github.com/nipoppy/nipoppy/blob/main/nipoppy/data/examples/sample_global_config-latest_pipelines.json) into it.

<!-- TODO add guide for generating manifest -->
```{attention}
It is extremely unlikely that the example manifest accurately represents your dataset, so you will have to generate one yourself.

The default [global configuration file](../user_guide/global_config.md) also has dataset-specific fields that you will need to replace.
```

Then the raw imaging data should be added to {{dpath_pre_reorg}} and reorganized with `nipoppy reorg` to prepare it for BIDS conversion. See [this guide](../user_guide/organizing_imaging.md) for more information.

## Starting with BIDS data

If the imaging data has already been converted to BIDS, we can use the `--bids-source` option to add it directly to the Nipoppy dataset:

```console
$ nipoppy init --dataset <PATH_TO_NEW_DATASET> --bids-source <PATH_TO_EXISTING_BIDS_DATA>
```

This will add the existing BIDS data to the {{dpath_bids}} directory and automatically generate a manifest file based on the participant IDs, session IDs and datatypes available in the BIDS data (based on directory names, not on any `participants.tsv` or `*_sessions.tsv` files).

```{attention}
If your study has additional visits that were not present in the BIDS data (e.g., non-imaging visits), you should manually add them to the manifest.
```

### BIDS data without sessions

If your BIDS data does not have session-level directories or `ses-` entities in filenames, we recommend redoing the BIDSification so that it has them.

:::{admonition} Why should I have sessions even if my data is cross-sectional?
:class: hint
We believe that having explicitly labelled sessions constitutes best practices:
1. It allows for more consistent organization across cross-sectional and longitudinal datasets
2. It will facilitate the addition of new sessions if follow-up data collection is carried out or if the study design becomes longitudinal
3. It may help link data between non-imaging and imaging visits
:::

If you decide to continue with session-less BIDS data, `nipoppy init` will still be able to generate a manifest file, but it will use a dummy value (`unnamed`) for the `visit_id` and `session_id` columns. You might also need to change some of the downstream pipeline configuration files because the default configurations typically assume that the BIDS data has sessions.
