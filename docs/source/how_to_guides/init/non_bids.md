# Initializing a new dataset starting with non-BIDS data

This guide shows how to initialize a new Nipoppy dataset for a study with source imaging data that consists of DICOM files or non-{term}`BIDS` NIfTI files.

The first step is to create an empty Nipoppy dataset using the [`nipoppy init`](../../cli_reference/init) command:

```console
$ nipoppy init --dataset <PATH_TO_NEW_DATASET>
```

This will create the directory tree and copy an [example manifest](https://github.com/nipoppy/nipoppy/blob/main/nipoppy/data/examples/sample_manifest.tsv) and an [example global configuration file](https://github.com/nipoppy/nipoppy/blob/main/nipoppy/data/examples/sample_global_config-latest_pipelines.json) into it.

<!-- TODO add guide for generating manifest -->
```{attention}
It is extremely unlikely that the example manifest accurately represents your dataset, so you will have to generate one yourself.

The default [global configuration file](../../user_guide/global_config.md) also has dataset-specific fields that you will need to replace.
```

Then the raw imaging data should be added (symlinked/copied/moved) to {{dpath_pre_reorg}} and reorganized with [`nipoppy reorg`](../../cli_reference/reorg) to prepare it for BIDS conversion. See [this guide](../../user_guide/organizing_imaging.md) for more information.
