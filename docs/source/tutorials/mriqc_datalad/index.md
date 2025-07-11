# Run MRIQC on a BIDS dataset with DataLad provenance tracking

This tutorial shows how to run the MRIQC pipeline on a BIDS dataset using DataLad for full provenance tracking. This is based on the [main MRIQC tutorial](../mriqc_from_bids/) but uses DataLad commands for reproducibility.

## Step 0: Download the BIDS dataset with DataLad

Instead of using the shell script method from the [main tutorial Step 0](../mriqc_from_bids/#step-0-download-the-bids-dataset), we'll use DataLad:

```console
$ datalad clone https://github.com/OpenNeuroDatasets/ds004101.git
$ datalad get -r ds004101
```

This downloads the dataset and gets all the data files, with full provenance tracking.

## Step 1: Initialize the Nipoppy dataset

**DataLad-first approach**: Create the DataLad dataset first, then initialize nipoppy inside it with `--force`:

```console
$ datalad create nipoppy_study
$ cd nipoppy_study
$ datalad run -m "Initialize nipoppy dataset" nipoppy init --bids-source ../ds004101 --force
```

This approach provides better provenance tracking by having DataLad track the nipoppy initialization step itself.

## Step 2: Modify the global configuration file

Follow [main tutorial Step 2](../mriqc_from_bids/#step-2-modify-the-global-configuration-file) exactly - no DataLad changes needed.

## Step 3: Install the MRIQC pipeline

Instead of the plain command from [main tutorial Step 3](../mriqc_from_bids/#step-3-install-the-mriqc-pipeline-into-the-dataset), use `datalad run` for provenance:

```console
$ datalad run -m "Install pipeline" nipoppy pipeline install 15427844
```

Then manually update the `TEMPLATEFLOW_HOME` in `global_config.json` as described in the main tutorial, and save the change:

```console
$ datalad save -m "set templateflow home"
```

## Step 4: Run MRIQC with DataLad provenance

Instead of the plain command from [main tutorial Step 4](../mriqc_from_bids/#step-4-run-mriqc-on-a-single-participant-and-session), use `datalad run`:

```console
$ datalad run -m "process single participant/session" nipoppy process \
--pipeline mriqc \
--pipeline-version 23.1.0 \
--participant-id 09114 \
--session-id 1pre
```

## Step 5: Track the pipeline processing status

Follow [main tutorial Step 5](../mriqc_from_bids/#step-5-track-the-pipeline-processing-status) exactly, then save the tracking results:

```console
$ datalad run -m "Track processing status" nipoppy track-processing \
    --dataset nipoppy_study \
    --pipeline mriqc \
    --pipeline-version 23.1.0
```
