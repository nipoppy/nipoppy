from pathlib import Path
import os

## Status flags
SUCCESS="SUCCESS"
FAIL="FAIL"
INCOMPLETE="INCOMPLETE"
UNAVAILABLE="UNAVAILABLE"

## dictionary for all output stages / file stems from TractoFlow in execution order

TractoFlow_Stages = {
    "All": [ 'Bet_Prelim_DWI', 'Denoise_DWI', 'Eddy', 'Topup', 'Eddy_Topup', 'Bet_DWI', 'N4_DWI', 'Crop_DWI', 'Normalize_DWI', 'Extract_B0', 'Resample_B0', 'Resample_DWI', 'Denoise_T1', 'N4_T1', 'Resample_T1', 'Bet_T1', 'Crop_T1', 'Register_T1', 'Segment_Tissues', 'Extract_DTI_Shell', 'Extract_FODF_Shell', 'DTI_Metrics', 'FODF_Metrics', 'Compute_FRF', 'PFT_Tracking_Maps', 'PFT_Seeding_Mask', 'PFT_Tracking' ],
    "DWIPreproc": [ 'Bet_Prelim_DWI', 'Denoise_DWI', 'Eddy', 'Topup', 'Eddy_Topup', 'Bet_DWI', 'N4_DWI', 'Crop_DWI', 'Normalize_DWI', 'Extract_B0', 'Resample_B0', 'Resample_DWI' ],
    "DWIPreprocEddyTopup": [ 'Bet_Prelim_DWI', 'Denoise_DWI', 'Eddy', 'Topup', 'Eddy_Topup' ],
    "DWIPreprocResampled":[ 'Bet_DWI', 'N4_DWI', 'Crop_DWI', 'Normalize_DWI', 'Extract_B0', 'Resample_B0', 'Resample_DWI' ],
    "AnatPreproc": [ 'Denoise_T1', 'N4_T1', 'Resample_T1', 'Bet_T1', 'Crop_T1', 'Register_T1', 'Segment_Tissues' ],
    "AnatResample": [ 'Denoise_T1', 'N4_T1', 'Resample_T1' ],
    "AnatSegment": [ 'Bet_T1', 'Crop_T1', 'Register_T1', 'Segment_Tissues' ],
    "DWIModel": [ 'Extract_DTI_Shell', 'Extract_FODF_Shell', 'DTI_Metrics', 'FODF_Metrics', 'Compute_FRF' ],
    "DWITensor": [ 'Extract_DTI_Shell', 'DTI_Metrics' ],
    "DWIFODF": [ 'Extract_FODF_Shell', 'FODF_Metrics', 'Compute_FRF' ],
    "Tracking": [ 'PFT_Tracking_Maps', 'PFT_Seeding_Mask', 'PFT_Tracking' ]
}

# , 'Local_Tracking_Mask', 'Local_Seeding_mask', 'Local_Tracking'

TractoFlow_Procs = { 
    "Bet_Prelim_DWI": [ '__b0_bet_mask_dilated.nii.gz', '__b0_bet_mask.nii.gz', '__b0_bet.nii.gz' ],
    "Denoise_DWI":  [ '__dwi_denoised.nii.gz' ],
    "Eddy":  [ '__bval_eddy', '__dwi_corrected.nii.gz', '__dwi_eddy_corrected.bvec' ],
    "Topup":  [ '__corrected_b0s.nii.gz', '__rev_b0_warped.nii.gz', 'topup_results_fieldcoef.nii.gz', 'topup_results_movpar.txt' ], 
    "Eddy_Topup":  [ '__b0_bet_mask.nii.gz', '__bval_eddy', '__dwi_corrected.nii.gz', '__dwi_eddy_corrected.bvec' ],
    "Bet_DWI":  [ '__b0_bet_mask.nii.gz', '__b0_bet.nii.gz', '__dwi_bet.nii.gz' ],
    "N4_DWI":  [ '__dwi_n4.nii.gz' ],
    "Crop_DWI":  [ '__b0_cropped.nii.gz', '__b0_mask_cropped.nii.gz', '__dwi_cropped.nii.gz' ],
    "Normalize_DWI":  [ '__dwi_normalized.nii.gz', '_fa_wm_mask.nii.gz' ],
    "Extract_B0":  [ '__b0.nii.gz' ],
    "Resample_B0":  [ '__b0_mask_resampled.nii.gz', '__b0_resampled.nii.gz' ],
    "Resample_DWI":  [ '__dwi_resampled.nii.gz' ],
    "Extract_DTI_Shell":  [ '__bval_dti', '__bvec_dti', '__dwi_dti.nii.gz' ],
    "Extract_FODF_Shell":  [ '__bval_fodf', '__bvec_fodf', '__dwi_fodf.nii.gz' ],
    "DTI_Metrics":  [ '__ad.nii.gz', '__evecs.nii.gz', '__ga.nii.gz', '__pulsation_std_dwi.nii.gz', '__residual_q1_residuals.npy', '__tensor.nii.gz', '__evals_e1.nii.gz', '__evecs_v1.nii.gz', '__md.nii.gz', '__rd.nii.gz', '__residual_q3_residuals.npy', '__evals_e2.nii.gz', '__evecs_v2.nii.gz', '__mode.nii.gz', '__residual_iqr_residuals.npy', '__residual_residuals_stats.png', '__evals_e3.nii.gz', '__evecs_v3.nii.gz', '__nonphysical.nii.gz', '__residual_mean_residuals.npy', '__residual_std_residuals.npy', '__evals.nii.gz', '__fa.nii.gz', '__norm.nii.gz', '__residual.nii.gz', '__rgb.nii.gz' ],
    "FODF_Metrics":  [ '__afd_max.nii.gz', '__afd_sum.nii.gz', '__afd_total.nii.gz', '__fodf.nii.gz', '__nufo.nii.gz', '__peak_indices.nii.gz', '__peaks.nii.gz' ],
    "Compute_FRF":  [ '__frf.txt' ],
    "Denoise_T1":  [ '__t1_denoised.nii.gz' ],
    "N4_T1":  [ '__t1_n4.nii.gz' ],
    "Resample_T1":  [ '__t1_resampled.nii.gz' ],
    "Bet_T1":  [ '__t1_bet_mask.nii.gz', '__t1_bet.nii.gz' ],
    "Crop_T1":  [ '__t1_bet_cropped.nii.gz', '__t1_bet_mask_cropped.nii.gz' ],
    "Register_T1":  [ '__output0GenericAffine.mat', '__output1InverseWarp.nii.gz', '__output1Warp.nii.gz', '__t1_mask_warped.nii.gz', '__t1_warped.nii.gz' ],
    "Segment_Tissues":  [ '__map_csf.nii.gz', '__map_gm.nii.gz', '__map_wm.nii.gz', '__mask_csf.nii.gz', '__mask_gm.nii.gz', '__mask_wm.nii.gz' ],
    "PFT_Tracking_Maps":  [ '__interface.nii.gz', '__map_exclude.nii.gz', '__map_include.nii.gz' ],
    "PFT_Seeding_Mask": [ '__pft_seeding_mask.nii.gz' ],
    "PFT_Tracking": [ '__pft_wholebrain_tracking.trk' ]
}

    # "Local_Tracking_Mask": [ '__?' ],
    # "Local_Seeding_Mask": [ '__?' ],
    # "Local_Tracking": [ '__?' ]

##
## define functions to check if the files exist / stages complete
##

def check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='All'):    
    """ docstring here
    """
    ## build subject info
    session = f"ses-{session_id}"
    run = f"run-{run_id}"
    participant_id = os.path.basename(subject_dir)

    ## default to incomplete
    status_msg = UNAVAILABLE

    ## turn off local tracking - configure as an optional step?
    doLocalTracking = False

    ## the valid options for task
    if not (task in list(stage_dict.keys())):
        raise ValueError("The requested report is not recognized.")

    ## pull the processes to check files for
    procs = stage_dict[task]

    ## check if Topup output exists - if it does, drop Eddy, otherwise drop Topup/Eddy_Topup
    if os.path.exists(subject_dir + '/Topup'):
        try:
            procs.remove('Eddy')
        except ValueError:
            pass
    else:
        try:
            procs.remove('Topup')
            procs.remove('Eddy_Topup')
        except ValueError:
            pass

    # ## drop local tracking
    # if (task=='Tracking'):
    #     if not doLocalTracking:
    #         procs.remove('Local_Tracking_Mask')
    #         procs.remove('Local_Seeding_Mask')
    #         procs.remove('Local_Tracking')

    ## build the filepaths of the files that are supposed to exist
    files = []
    for proc in procs:
        for stem in file_check_dict[proc]:
            if stem[0] == '_':
                files.append(os.path.join(subject_dir, proc, participant_id + stem))
            else:
                files.append(os.path.join(subject_dir, proc, stem))
                
    ## build logical if files exist
    filesExist = [ os.path.exists(out) for out in files ]
    
    ## fill in possible status files
    if any(filesExist):
        if all(filesExist):
            status_msg = SUCCESS
        else:
            status_msg = INCOMPLETE
    elif not os.path.exists(subject_dir):
        status_msg = UNAVAILABLE
    else:
        status_msg = FAIL
    
    ## return status
    return status_msg

def check_dwiPreproc(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWIPreproc')
    return status_msg

def check_anatPreproc(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='AnatPreproc')
    return status_msg

def check_dwiModel(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWIModel')
    return status_msg

def check_pftTracking(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='Tracking')
    return status_msg

def check_dwiPreprocEddyTopup(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWIPreprocEddyTopup')
    return status_msg

def check_dwiNormalize(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWIPreprocResampled')
    return status_msg

def check_anatReorient(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='AnatResample')
    return status_msg

def check_anatTracking(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='AnatSegment')
    return status_msg

def check_dwiModelTensor(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWITensor')
    return status_msg

def check_dwiModelFODF(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='DWIFODF')
    return status_msg

def check_tf_final(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages):
    """ docstring here
    """
    status_msg = check_tf_output(subject_dir, session_id, run_id, file_check_dict=TractoFlow_Procs, stage_dict=TractoFlow_Stages, task='All')
    return status_msg

## the dictionary to return with the inspected outputs

tracker_configs = {
    "pipeline_complete": check_tf_final,    
    "PHASE_": {
            "DWI-Preprocessing": check_dwiPreproc,
            "Anat-Preprocessing": check_anatPreproc,
            "DWI-ModelFitting": check_dwiModel,
            "PFT-Tracking": check_pftTracking
            },
    "STAGE_": {
            "DWI-Preproc-EddyTopup": check_dwiPreprocEddyTopup,
            "DWI-Preproc-Normalize": check_dwiNormalize,
            "Anat-Preproc-Reorient": check_anatReorient,
            "Anat-Preproc-Tracking": check_anatTracking,
            "DWI-ModelFitting-Tensor": check_dwiModelTensor,
            "DWI-ModelFitting-fODF": check_dwiModelFODF
    }
}
