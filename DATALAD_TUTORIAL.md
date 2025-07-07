# Run MRIQC on a BIDS dataset with DataLad provenance tracking

This tutorial shows how to run the MRIQC pipeline on a BIDS dataset using DataLad for full provenance tracking. This is based on the main tutorial at `docs/source/tutorials/mriqc_from_bids/index.md` but uses DataLad commands for reproducibility.

## Step 0: Download the BIDS dataset with DataLad

Instead of using the shell script method from the [main tutorial Step 0](docs/source/tutorials/mriqc_from_bids/index.md#step-0-download-the-bids-dataset), we'll use DataLad:

```console
$ datalad clone https://github.com/OpenNeuroDatasets/ds004101.git 
$ datalad get -r ds004101
```

This downloads the dataset and gets all the data files, with full provenance tracking.

## Step 1: Initialize the Nipoppy dataset

Same as [main tutorial Step 1](docs/source/tutorials/mriqc_from_bids/index.md#step-1-initialize-the-nipoppy-dataset):

```console
$ nipoppy init --dataset nipoppy_study --bids-source ds004101
```

**DataLad addition**: Turn the nipoppy study into a DataLad dataset for tracking:

```console
$ cd nipoppy_study
$ datalad create --force .
$ datalad save -m "nipoppy init"
```

# TODO Yarik?
Note: The bids-source creates a symlink rather than a proper DataLad subdataset link, which isn't ideal for full provenance.
Personally, I'd prefer to do nipoppy init from an existing but empty datalad repo.

## Step 2: Modify the global configuration file

Follow [main tutorial Step 2](docs/source/tutorials/mriqc_from_bids/index.md#step-2-modify-the-global-configuration-file) exactly - no DataLad changes needed.

## Step 3: Install the MRIQC pipeline 

Instead of the plain command from [main tutorial Step 3](docs/source/tutorials/mriqc_from_bids/index.md#step-3-install-the-mriqc-pipeline-into-the-dataset), use `datalad run` for provenance:

```console
$ datalad run -m "Install pipeline" nipoppy pipeline install 15427844
```

Then manually update the `TEMPLATEFLOW_HOME` in `global_config.json` as described in the main tutorial, and save the change:

```console
$ datalad save -m "set templateflow home"
```

## Step 4: Run MRIQC with DataLad provenance

Instead of the plain command from [main tutorial Step 4](docs/source/tutorials/mriqc_from_bids/index.md#step-4-run-mriqc-on-a-single-participant-and-session), use `datalad run`:

```console
$ datalad run -m "process single participant/session" nipoppy process \
--pipeline mriqc \
--pipeline-version 23.1.0 \
--participant-id 09114 \
--session-id 1pre
```

## Step 5: Track the pipeline processing status

Follow [main tutorial Step 5](docs/source/tutorials/mriqc_from_bids/index.md#step-5-track-the-pipeline-processing-status) exactly, then save the tracking results:

```console
$ datalad run -m "Track processing status" nipoppy track-processing \
    --dataset nipoppy_study \
    --pipeline mriqc \
    --pipeline-version 23.1.0
```
