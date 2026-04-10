# Convert MRI sourcedata to BIDS

In this tutorial, you will learn how to use Nipoppy and the BIDS app [dcm2bids](https://unfmontreal.github.io/Dcm2Bids/3.2.0/) to convert your imaging sourcedata to BIDS.

Concretely, we will:
1. Initialize a Nipoppy dataset
2. Reorganize dicom sourcedata
3. Install and set up the dcm2bids pipeline
4. Extract dicom header information to create the `decm2bids_config.json`
5. Convert the dicom sourcedata to nifti BIDS raw data
6. Track the output files to check if the conversion was successful

```{note}
If you have not installed Nipoppy yet, instructions are available [here](../../overview/installation).
```

```{attention}
This tutorial assumes that [Apptainer](https://apptainer.org) (or Singularity) is installed on your system. If that is not the case, then you will not be able to run dcm2bids with Nipoppy.
```

## Step 0: Download the tutorial dataset

We will use the [tutorial dataset](https://github.com/nipoppy/tutorial-dataset) provided on the Nipoppy GitHub, which includes dicom data of different modalities for 4 subjects (*Note: Data of one subject was copied in order to create multiple subjects with different modalities for training purposes. Hence, all data stems from one subject*).

There are multiple ways of downloading the dataset:

**1. via `git clone`**

ssh: `git clone git@github.com:nipoppy/tutorial-dataset.git`

https: `git clone https://github.com/nipoppy/tutorial-dataset.git`

**2. via the browser:**

- Go to [https://github.com/nipoppy/tutorial-dataset](https://github.com/nipoppy/tutorial-dataset)
- Click on the green button "Code" on the right upper corner on the repo site and select "Download Zip"

**3. via the command line:**

```
wget -O tutorial-dataset.zip https://github.com/nipoppy/tutorial-datset/archive/refs/heads/main.zip
```
Unzip once downloaded.

## Step 1: Initialize the Nipoppy dataset

**1.1.** Run the following command to create a Nipoppy dataset:

```console
$ nipoppy init --dataset nipoppy_study
```

This command creates a folder named `nipoppy_study` with subdirectories for raw data, processed (derivatives) data, pipeline configuration files, logs, etc. The `tree` command can be used to show the directory structure.

```console
$ tree -L 1 nipoppy_study
```

```{code-block}
:caption: Output
nipoppy_study/
├── bids
├── code
├── containers
├── derivatives
├── global_config.json
├── logs
├── manifest.tsv
├── pipelines
├── scratch
├── sourcedata
└── tabular
```

**1.2.** Please replace the `manifest.tsv` in `nipoppy_study` with the `manifest.tsv` provided in the tutorial dataset. This file is considered the ground truth for which participants and sessions are available for processing.

## Step 2: Reorganize the dicom sourcedata

**Why reorganization?:** Usually, there is a gap between data state out of scanner vs. ready for bidsification. Source data is often messy in different ways, making it hard to use BIDSification tools directly. Nipoppy provides a unified way to deal with DICOM vs. Nifti sourcedata which simplifies BIDSification. It also helps fixing issues related to file naming which often appear in chaotic data dumps or due to typos. Additionally, the organization simplifies taring the DICOMs after bidsification. All this is implemented in one simple command, namely [`nipoppy reorg`](../../cli_reference/reorg.rst).

**2.1.** We need to move the **content** of the `tutorial-dataset/reorg` directory to the `sourcedata/imaging/pre_reorg` directory of our `nipoppy_study` dataset, i.e.:

```console
mv tutorial-dataset/reorg/* nipoppy_study/sourcedata/imaging/pre_reorg
```

Running

```console
nipoppy status --dataset nipoppy_study
```

should give us the following output:

```{code-block}
:caption: Output
     Participant counts by session at each Nipoppy checkpoint
            ╷             ╷
 session_id │ in_manifest │ in_pre_reorg
════════════╪═════════════╪════════════════
    01      │      4      │      4
            ╵             ╵
```

**2.2.** We run

```console
nipoppy reorg --dataset nipoppy_study
```

Our data was symlinked and reorganized into the `post_reorg` directory. We can see so by running `nipoppy status`:

```{code-block}
:caption: Output
     Participant counts by session at each Nipoppy checkpoint
            ╷             ╷
 session_id │ in_manifest │ in_post_reorg
════════════╪═════════════╪════════════════
    01      │      4      │      4
            ╵             ╵
```

## Step 3: Install and set up the dcm2bids pipeline

**3.1.** The `nipoppy init` command created the configuration file at `nipoppy_study/global_config.json`. This file may need to be updated with information specific to your computing environment. Initially, it will look like this:

```{literalinclude} ../../../../nipoppy/data/examples/sample_global_config.json
---
linenos: True
language: json
emphasize-lines: 4,9
---
```

By default, this file does not contain any pipeline-specific information, since the dataset does not have any pipelines installed yet. Still, there are fields that may need to be modified depending on your setup:
- If you are on a system that still uses Singularity (which has been renamed to Apptainer), you will need to change `CONTAINER_CONFIG` -> `COMMAND` to `"singularity"` instead of `"apptainer"`
- If your group uses a shared directory for storing container image files, you can replace the value of `"[[NIPOPPY_DPATH_CONTAINERS]]"` by the full path to that shared directory. For example:
    ```json
    "SUBSTITUTIONS": {
        "_comment": "Self-references like NIPOPPY_DPATH_CONTAINERS are resolved from the layout at runtime, making them layout-aware",
        "[[NIPOPPY_DPATH_CONTAINERS]]": "<PATH_TO_SHARED_DIRECTORY>",
        "[[HPC_ACCOUNT_NAME]]": ""
    },
    ```
    - Alternatively, you can create a symlink from {{dpath_containers}} to that directory (then this line in the configuration can be deleted) (recommended).

**3.2.** We can use following command to check which pipelines can be run with the dataset:

```console
$ nipoppy pipeline list --dataset nipoppy_study
```

The output says that there are no available pipelines to be run:
```
INFO     No available bidsification pipelines
INFO     No available processing pipelines
INFO     No available extraction pipelines
```

That is because a newly initialized Nipoppy dataset does not contain any pipelines. Pipeline configuration files are available on the [Zenodo data repository](https://zenodo.org/search?q=metadata.subjects.subject%3A%22Nipoppy%22&l=list&p=1&s=10&sort=bestmatch) and can be searched for directly from your terminal using the command `nipoppy pipeline search`. The [configuration files for dcm2bids](https://zenodo.org/records/16876754) can be downloaded by running the following:
```{code-block} console
$ nipoppy pipeline install --dataset nipoppy_study {{zenodo_id_dcm2bids_3_2_0}}
```

When running `nipoppy pipeline install`, you will be asked if you would like to download the dcm2bids container. If you do not already have a download of the container, type `y` and press `Enter` to do so. The download/building process may take ~10 minutes. The container image will be downloaded as `dcm2bids_3.2.0.sif` inside the container store directory (i.e., `nipoppy_study/containers` or the custom path you set in the `global_config.json` file).

**3.3.** When we open the `nipoppy_study/global_config.json`, we can see that the pipeline expects some more configuration (indicated by the null placeholder):

```{code-block} json
:emphasize-lines: 5
    "PIPELINE_VARIABLES": {
        "BIDSIFICATION": {
            "dcm2bids": {
                "3.2.0": {
                    "DCM2BIDS_CONFIG_FILE": null
                }
            }
        },
        "PROCESSING": {},
        "EXTRACTION": {}
    },
```

## Step 4: Extract dicom header information to create the `decm2bids_config.json`

When we look at the bidsify command options with `nipoppy bidsify -h`, we see that this command can be run with different steps.  Those steps are “prepare” and “convert”. The “prepare” step will help you to get the information you need to later pass to the “convert” step, namely the content for the `dcm2bids_config.json`. This said content holds information to determine which sequences  from the entire MRI acquisition protocol will be converted to NIfTIs, and how they will be named based on BIDS standard. The information for this config file will be extracted from one participant’s dicom images’ headers, which we obtain from the nipoppy bidsify prepare step. The output will be saved under `scratch/dcm2bids_helper`. From this output, we can create the `dcm2bids_config.json`.

**4.1.** We run
```console
nipoppy bidsify --dataset nipoppy_study --pipeline dcm2bids --pipeline-version 3.2.0 --pipeline-step prepare
```

In our scratch directory we should see something like this now:
```
scratch/
├── dcm2bids_helper
│   ├── 013_post_reorg_T1_mprage_1mm_20180706110327.json
│   ├── 013_post_reorg_T1_mprage_1mm_20180706110327.nii.gz
│   ├── 015_post_reorg_DTI_30_DIRs_A-P_20180706110327.bval
│   ├── 015_post_reorg_DTI_30_DIRs_A-P_20180706110327.bvec
│   ├── 015_post_reorg_DTI_30_DIRs_A-P_20180706110327.json
│   ├── 015_post_reorg_DTI_30_DIRs_A-P_20180706110327.nii.gz
│   ├── 018_post_reorg_restingstate_20180706110327.json
│   └── 018_post_reorg_restingstate_20180706110327.nii.gz
```

The dcm2bids_helper command which is used by the nipoppy bidsify prepare step turned one participant's DICOMS into NIfTI files with their accompanying json metadata files. Our task is now to find unique metadata or descriptions in each modalitie's json file, so that dcm2bids knows how to group a set of acquisitions and how to label them according to BIDS, meaning we need to link the metadata to BIDS specific vocabulary.

Unique entries in the json files can be `SeriesDescription`, `EchoTime`, `ProtocolName`, `ImageType` etc. Whatever makes the files acquired under one condition different from other files acquired under different conditions. Also, we need to tell dcm2bids to which BIDS datatype this acquisition refers to and which BIDS suffix this file is going to have, so you need some knowledge of the [BIDS specification](https://bids-specification.readthedocs.io/en/stable/) for this task.

In our case, the `dcm2bids_config.json` can look like this:

```{code-block} json
{
    "descriptions": [
      {
        "datatype": "anat",
        "suffix": "T1w",
        "criteria": {
          "SeriesDescription": "T1_mprage_1mm"
        }
      },
      {
        "datatype": "func",
        "suffix": "bold",
        "custom_entities": "task-rest",
        "criteria": {
          "SeriesDescription": "restingstate",
        "sidecar_changes": {
          "TaskName": "rest"
          }
        }
      },
      {
      "datatype": "dwi",
      "suffix": "dwi",
      "criteria": {
        "SeriesDescription": "DTI_30_DIRs_A-P"
        }
      }
    ]
  }
```

**4.2.** We create a `dcm2bids_config.json` with the above content and place it in the `code` directory in our `nipoppy_study`dataset.

**4.3.** We open Nipoppy's `global_config.json` and replace the `null` behind the `dcm2bids_config_file` with the right directory:

```{code-block} json
:emphasize-lines: 5
    "PIPELINE_VARIABLES": {
        "BIDSIFICATION": {
            "dcm2bids": {
                "3.2.0": {
                    "DCM2BIDS_CONFIG_FILE": "code/dcm2bids_config.json"
                }
            }
        },
        "PROCESSING": {},
        "EXTRACTION": {}
    },
```

## Step 5: Convert the dicom sourcedata to nifti BIDS raw data

**5.1.** We are now ready to run

```console
nipoppy bidsify --dataset nipoppy_study --pipeline dcm2bids --pipeline-version 3.2.0 --pipeline-step convert
```

After successful conversion, the output of `nipoppy status` should look like this now:

```{code-block}
:caption: Output
     Participant counts by session at each Nipoppy checkpoint
            ╷             ╷
 session_id │ in_manifest │ in_bids
════════════╪═════════════╪═════════
    01      │      4      │      4
            ╵             ╵
```
