import argparse
import json
import subprocess
import os
from pathlib import Path
# import nipoppy.workflow.logger as my_logger
import shutil
# import logging

import numpy as np

# Author: Brent McPherson
# Date: 2024-02-23


def create_dkt_atlas(inp_parc, out_parc):
    """
    Convert aparc.DKTatlas+aseg.mgz into a .nii.gz w/ only cortical labels.
    """

    import nibabel as nib

    # create the list of the DKT labels
    DKT_LABELS = np.array([1002, 1003, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015,
                           1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1028,
                           1029, 1030, 1031, 1034, 1035, 2002, 2003, 2005, 2006, 2007, 2008, 2009, 2010,
                           2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023,
                           2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2034, 2035])
    # check the types - these should be integers. Recast?
    # take as keyword list or raw input

    print('----------------------')
    print('Looking for DKT Labels')
    print('----------------------')

    print(f"There are {DKT_LABELS.shape[0]} expected labels.")
    print(f"The labels to keep are:\n{DKT_LABELS}")

    print('------------------------')
    print('Loading the parcellation')
    print('------------------------')

    # load the mgz
    dkt = nib.load(inp_parc)

    # print the file type labels are loaded from
    print(f"Parcellation loaded from: {dkt.get_filename()}")
    print(f"Volume data loaded from: {dkt.files_types[0][1]}")

    # extract the labels and the header
    lab = dkt.get_fdata()
    lab = lab.astype(np.int16)  # just cast as integer? how to check if this breaks?
    aff = dkt.affine

    # pull the shapes
    nlab = np.sum(lab > 0)
    slab = np.prod(lab.shape)

    # get the unique, non-zero labels
    ulab = np.unique(lab)
    ulab = ulab[ulab > 0]

    print(f"Input labels have dimension: {lab.shape}")
    print(f"There are {nlab} / {slab} voxels labeled ({(nlab/slab)*100:.2f}%).")

    print(f"There are {np.unique(lab).shape[0]} unique labels in the loaded volume.")
    print(f"The unique, non-zero labels in the input file are:\n{ulab}")

    # check the precision of data

    print('-------------------------')
    print('Dropped the unused labels')
    print('-------------------------')

    # find where the labels are not to build the mask
    idx = ~np.isin(lab, DKT_LABELS)

    # logical index the labels into the output volume
    out = np.ma.array(lab, mask=idx, fill_value=0)
    out = out.filled()  # filled back to regular array
    # check the types - these can be forced (?) to integers

    # pull the shapes
    nout = np.sum(out > 0)
    sout = np.prod(out.shape)

    print(f"Output labels have dimension: {out.shape}")
    print(f"There are {nout} / {sout} voxels labeled ({(nout/sout)*100:.2f}%).")

    # get the unique, non-zero labels
    uout = np.unique(out)
    uout = uout[uout > 0]

    print(f"There are {uout.shape[0]} unique labels in the output volume.")
    print(f"The unique, non-zero labels in the output are:\n{np.unique(uout)}")

    print('--------------------------')
    print('---Creating output file---')
    print('--------------------------')

    # create .nii.gz of the output data and affine
    nii = nib.nifti2.Nifti1Image(out, aff)

    # write the .nii.gz of the data to disk
    nib.save(nii, out_parc)

    print(f'Created output file: {out_parc}')


def create_structural(inp_labels, inp_tracks, inp_output):
    """
    From a list of input parcellations, create a count network adjacency matrix.

    Tractography is large and slow to load - this process loads it once for every label set.
    """

    import glob
    import pathlib
    import numpy as np
    import nibabel as nib
    from dipy.tracking import utils

    # input parcellations to loop over, sorted for consistent logs
    # parcs=np.sort(os.listdir(inp_labels))
    pfiles = glob.glob(os.path.join(inp_labels, '*space-dwi*dseg.nii.gz'))
    pfiles = np.sort(pfiles)
    pfiles = [pathlib.Path(x) for x in pfiles]
    parcs = [x.name for x in pfiles]

    print('Loading streamlines:', inp_tracks)

    # load streamlines
    trk = nib.streamlines.load(inp_tracks)

    # extract space of the streamlines
    affine = trk.affine

    # extract the streamlines
    streamlines = trk.streamlines

    print("Creating adjacency matrices for found dseg labels...")

    # loop found parcellations and create networks
    for parc in parcs:

        print('Loading parcellation:', parc)
        labels_file = nib.load(os.path.join(inp_labels, parc))
        labels = labels_file.get_fdata()

        np.unique(labels)

        print('Building the adjacency matrix with the loaded tractography and labels...')
        M, grouping = utils.connectivity_matrix(streamlines, affine, labels.astype(np.uint16),
                                                return_mapping=True, mapping_as_streamlines=True)

        # drop the first row / column (label 0 is background)
        M = M[1:, 1:]

        # create output name
        outf = os.path.join(inp_output, parc.replace('_dseg.nii.gz', '_conmat-count.tsv'))

        print('Saving the structural connectome:', outf)
        np.savetxt(outf, M, delimiter='\t')


def run(participant_id, global_configs, session_id, output_dir,
        tractoflow_dir, fmriprep_dir, freesurfer_dir, logger=None):
    """
    Parse the inputs to create the DKT and Schaefer networks for the requested participant
    """

    # copy fmriprep config parsing - minor extensions for tractoflow needed

    # extract paths
    DATASET_ROOT = global_configs["DATASET_ROOT"]
    TEMPLATEFLOW_DIR = global_configs["TEMPLATEFLOW_DIR"]
    CONTAINER_STORE = global_configs["CONTAINER_STORE"]
    FMRIPREP_CONTAINER = global_configs["PROC_PIPELINES"]["fmriprep"]["CONTAINER"]
    TRACTOFLOW_CONTAINER = global_configs["PROC_PIPELINES"]["tractoflow"]["CONTAINER"]
    FMRIPREP_VERSION = global_configs["PROC_PIPELINES"]["fmriprep"]["VERSION"]
    TRACTOFLOW_VERSION = global_configs["PROC_PIPELINES"]["tractoflow"]["VERSION"]
    FS_VERSION = global_configs["PROC_PIPELINES"]["freesurfer"]["VERSION"]
    FMRIPREP_CONTAINER = FMRIPREP_CONTAINER.format(FMRIPREP_VERSION)
    TRACTOFLOW_CONTAINER = TRACTOFLOW_CONTAINER.format(TRACTOFLOW_VERSION)

    # pick the container - I'm not sure fMRIPrep has Dipy - TractoFlow container definitely has ANTs / Dipy
    SINGULARITY_FMRIPREP = f"{CONTAINER_STORE}{FMRIPREP_CONTAINER}"
    SINGULARITY_TRACTOFLOW = f"{CONTAINER_STORE}{TRACTOFLOW_CONTAINER}"

    # set up logs
    #log_dir = f"{DATASET_ROOT}/scratch/logs"

    #if logger is None:
    #    log_file = f"{log_dir}/network_extractor.log"
    #    logger = my_logger.get_logger(log_file)

    #logger.info("-"*75)
    #logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
    #logger.info(f"Using participant_id: {participant_id}, session_id:{session_id}")
    # logger.info(f"Optional args: --anat_only={anat_only}, --use_bids_filter={use_bids_filter}")
    print(f"Using DATASET_ROOT: {DATASET_ROOT}")
    print(f"Using PARTICIPANT_ID: {participant_id}, SESSION_ID: {session_id}")

    if output_dir is None:
        output_dir = f"{DATASET_ROOT}/derivatives/networks/v0.9.0"

    if tractoflow_dir is None:
        tractoflow_dir = f"{DATASET_ROOT}/derivatives/tractoflow/{TRACTOFLOW_VERSION}/output/ses-{session_id}"

    if fmriprep_dir is None:
        fmriprep_dir = f"{DATASET_ROOT}/derivatives/fmriprep/{FMRIPREP_VERSION}/output"

    if freesurfer_dir is None:
        freesurfer_dir = f"{DATASET_ROOT}/derivatives/freesurfer/{FS_VERSION}/output/ses-{session_id}"

    # these paths build all the input / output files

    # define paths to outputs
    LABPATH = Path(output_dir)
    SEGPATH = Path(output_dir, f"sub-{participant_id}", f"ses-{session_id}", 'anat')
    NETPATH = Path(output_dir, f"sub-{participant_id}", f"ses-{session_id}", 'dwi')
    # FUNPATH = Path(output_dir, f"sub-{participant_id}", f"ses-{session_id}", 'func')
    # add functional as part of this? easy to load...

    # make output paths if they don't exist
    if ~os.path.exists(LABPATH):
        os.makedirs(LABPATH)

    if ~os.path.exists(SEGPATH):
        os.makedirs(SEGPATH)

    if ~os.path.exists(NETPATH):
        os.makedirs(NETPATH)

    # SPLIT HERE TO MAKE run_extractor() FOR EASIER INVOCATION
    # ... IT DOES NOT MAKE IT EASIER...

    # the input results directories, passed inputs
    TF_PATH = tractoflow_dir
    FP_PATH = fmriprep_dir
    FS_PATH = freesurfer_dir

    # create full path file names for inputs / ouptuts

    # space to freesurfer .mgz DKT labels
    DKT_MGZ = Path(FS_PATH, f"ses-{session_id}", f"sub-{participant_id}", 'mri', 'aparc.DKTatlas+aseg.mgz')

    # output paths for converted DKT labels
    DKT_NII = Path(SEGPATH, f"sub-{participant_id}_ses-{session_id}_space-fsnative_atlas-DKTatlas+aseg_dseg.nii.gz")
    DKT_MNI = Path(SEGPATH, f"sub-{participant_id}_ses-{session_id}_space-MNI152NLin2009cAsym_atlas-DKTatlas+aseg_dseg.nii.gz")
    DKT_DWI = Path(SEGPATH, f"sub-{participant_id}_ses-{session_id}_space-dwi_atlas-DKTatlas+aseg_dseg.nii.gz")

    # paths to ANTs xfom files
    ANAT2MNI_ALL = Path(FP_PATH, f"sub-{participant_id}", f"ses-{session_id}", 'anat', f"sub-{participant_id}_ses-{session_id}_run-1_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5")
    MNI2ANAT_ALL = Path(FP_PATH, f"sub-{participant_id}", f"ses-{session_id}", 'anat', f"sub-{participant_id}_ses-{session_id}_run-1_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5")
    FS2ANAT_AFF = Path(FP_PATH, f"sub-{participant_id}", f"ses-{session_id}", 'anat', f"sub-{participant_id}_ses-{session_id}_run-1_from-fsnative_to-T1w_mode-image_xfm.txt")

    # path to space-dwi T1 image
    ANAT_DWI = Path(TF_PATH, f"sub-{participant_id}", 'Register_T1', f"sub-{participant_id}__t1_warped.nii.gz")

    # paths to tractoflow native alignment files
    ANAT2DWI_AFF = Path(TF_PATH, f"sub-{participant_id}", 'Register_T1', f"sub-{participant_id}__output0GenericAffine.mat")
    ANAT2DWI_SYN = Path(TF_PATH, f"sub-{participant_id}", 'Register_T1', f"sub-{participant_id}__output1Warp.nii.gz")
    TRACTOGRAPHY = Path(TF_PATH, f"sub-{participant_id}", 'PFT_Tracking', f"sub-{participant_id}__pft_tracking_prob_wm_seed_0.trk")

    # path to templateflow space / labels / reference volume
    MNIPATH = Path(TEMPLATEFLOW_DIR, 'tpl-MNI152NLin2009cAsym')
    MNITEMP = Path(MNIPATH, 'tpl-MNI152NLin2009cAsym_res-02_T1w.nii.gz')

    # convert the DKT cortical parcellation from .mgz to .nii.gz
    create_dkt_atlas(DKT_MGZ, DKT_NII)

    # copy the full set of labels - Ideally prune down to just the cortical...
    if ~os.path.exists(Path(LABPATH, f"atlas-DKT_dseg.tsv")):
        print("Copy DKT labels file to output")
        shutil.copyfile(Path(TEMPLATEFLOW_DIR, 'tpl-fsaverage', "tpl-fsaverage_dseg.tsv"),
                        Path(LABPATH, f"atlas-DKT_dseg.tsv"))

    # convert DKT cortical labels to MNI space
    # subprocess.run(f'antsApplyTransforms -d 3 -e 0 -i {DKT_NII} -r {MNITEMP} -o {DKT_MNI} -n GenericLabel -v 1 -t {ANAT2MNI_ALL} {FS2ANAT_AFF}')
    sub_dkt_mni = f'antsApplyTransforms -d 3 -e 0 -i {DKT_NII} -r {MNITEMP} -o {DKT_MNI} -n GenericLabel -v 1 -t {ANAT2MNI_ALL} {FS2ANAT_AFF}'
    cmd_dkt_mni = sub_dkt_mni.split()
    subprocess.run(cmd_dkt_mni)

    # convert DKT cortical labels into participant DWI space
    # subprocess.run(f'antsApplyTransforms -d 3 -e 0 -i {DKT_NII} -r {ANAT_DWI} -o {DKT_DWI} -n GenericLabel -v 1 -t {ANAT2DWI_SYN} {ANAT2DWI_AFF} {FS2ANAT_AFF}')
    sub_dkt_dwi = f'antsApplyTransforms -d 3 -e 0 -i {DKT_NII} -r {ANAT_DWI} -o {DKT_DWI} -n GenericLabel -v 1 -t {ANAT2DWI_SYN} {ANAT2DWI_AFF} {FS2ANAT_AFF}'
    cmd_dkt_dwi = sub_dkt_dwi.split()
    subprocess.run(cmd_dkt_dwi)

    # define Schaefer 2018 resolutions
    schaeferRes = [100, 200, 300, 400, 500, 600, 800, 1000]
    schaeferLab = [7, 17]

    # create a flat list combination of the labels
    schaeferOut = np.array([(x, y) for x in schaeferRes for y in schaeferLab])

    # for every Schaefer resolution / label pair
    for out in schaeferOut:

        # copy the labels to the output if they don't already exist there
        if ~os.path.exists(Path(LABPATH, f"atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.tsv")):
            print("Copy labels file to output")
            shutil.copyfile(Path(TEMPLATEFLOW_DIR, 'tpl-MNI152NLin2009cAsym', f"tpl-MNI152NLin2009cAsym_atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.tsv"),
                            Path(LABPATH, f"atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.tsv"))

        # warp the corresponding resolution / label file to the DWI space
        # subprocess.run(f'antsApplyTransforms -d 3 -e 0 -i {MNIPATH}/tpl-MNI152NLin2009cAsym_res-02_atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.nii.gz -r {ANAT_DWI} -o {SEGPATH}/sub-{participant_id}_ses-{session_id}_space-dwi_atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.nii.gz -n GenericLabel -v 1 -t {ANAT2DWI_SYN} {ANAT2DWI_AFF} {MNI2ANAT_ALL}')
        sub_ant_dwi = f'antsApplyTransforms -d 3 -e 0 -i {MNIPATH}/tpl-MNI152NLin2009cAsym_res-02_atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.nii.gz -r {ANAT_DWI} -o {SEGPATH}/sub-{participant_id}_ses-{session_id}_space-dwi_atlas-Schaefer2018_desc-{out[0]}Parcels{out[1]}Networks_dseg.nii.gz -n GenericLabel -v 1 -t {ANAT2DWI_SYN} {ANAT2DWI_AFF} {MNI2ANAT_ALL}'
        cmd_ant_dwi = sub_ant_dwi.split()
        subprocess.run(cmd_ant_dwi)

    # for all of the converted labels, create an adjacency network in a .tsv
    create_structural(SEGPATH, TRACTOGRAPHY, NETPATH)


if __name__ == '__main__':

    HELPTEXT = """
    Extract count networks from TractoFlow and fMRIPrep derivatives.
    """

    # parse arguments

    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--global_config', type=str, help='path to global configs for a given nipoppy dataset')
    parser.add_argument('--participant_id', type=str, help='participant id')
    parser.add_argument('--session_id', type=str, help='session id for the participant')
    parser.add_argument('--output_dir', type=str, default=None, help='specify custom output dir (if None --> <DATASET_ROOT>/derivatives)')

    parser.add_argument('--tractoflow', type=str, default=None, help='path to TractoFlow output to create networks')
    parser.add_argument('--fmriprep', type=str, default=None, help='path to fMRIPrep output to create networks')
    parser.add_argument('--freesurfer', type=str, default=None, help='path to FreeSurfer output to create networks')
    # other result directories?

    args = parser.parse_args()

    global_config_files = args.global_config
    participant_id = args.participant_id
    session_id = args.session_id
    output_dir = args.output_dir

    tractoflow_dir = args.tractoflow
    fmriprep_dir = args.fmriprep
    freesurfer_dir = args.freesurfer

    # load inputs

    # load global config
    with open(global_config_files, 'r') as f:
        global_configs = json.load(f)

    # invoke run command
    run(participant_id, global_configs, session_id, output_dir, tractoflow_dir, fmriprep_dir, freesurfer_dir)
