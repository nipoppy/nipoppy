# Initializing a new dataset starting with BIDS data

This guide shows how to initialize a new Nipoppy dataset for a study with {term}`BIDS` imaging data already available.

We can use the [`nipoppy init`](../../cli_reference/init) command with the `--bids-source` option to directly add the BIDS directory to the Nipoppy dataset:

```console
$ nipoppy init --dataset <PATH_TO_NEW_DATASET> --bids-source <PATH_TO_EXISTING_BIDS_DATA>
```

This will add the existing BIDS data to the {{dpath_bids}} directory and automatically generate a manifest file based on the participant IDs, session IDs and datatypes available in the BIDS data (based on directory names, not on any `participants.tsv` or `*_sessions.tsv` files).

```{attention}
If your study has additional visits that were not present in the BIDS data (e.g., non-imaging visits), you should manually add them to the manifest.
```

## BIDS data without sessions

If your BIDS data does not have session-level directories or `ses-` entities in filenames, we recommend redoing the BIDSification so that it has them.

:::{admonition} Why should I have sessions even if my data is cross-sectional?
:class: hint
We believe that having explicitly labelled sessions constitutes best practices:
1. It allows for more consistent organization across cross-sectional and longitudinal datasets
2. It will facilitate the addition of new sessions if follow-up data collection is carried out or if the study design becomes longitudinal
3. It may help link data between non-imaging and imaging visits
:::

If you decide to continue with session-less BIDS data, `nipoppy init` will still be able to generate a manifest file, but it will use a dummy value (`unnamed`) for the `visit_id` and `session_id` columns. You might also need to change some of the downstream pipeline configuration files because the default configurations typically assume that the BIDS data has sessions.
