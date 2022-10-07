#!/bin/bash

## take subject as input
SUBJ=$1

## path to singularity image
SINGULARITY_IMAGE=/data/pd/qpn/proc/containers/tractoflow_2.2.1_b9a527_2021-04-13.sif

## number of cores
NCORE=4

##
## build paths
##

## input data from bids structure
DATADIR=/data/pd/qpn/bids
BIDSDIR=${DATADIR}/${SUBJ}/ses-01

## BIDS derivative output folder in pipeline directory along with paths for logs
OUTPUT=/data/pd/qpn/tractoflow/derivatives/tractoflow/v2.2.1/output/tractoflow
LOGDIR=/data/pd/qpn/tractoflow/bin/jobs/logs

## move outputs
# /data/pd/qpn/tractoflow/derivatives/tractoflow
# /data/pd/qpn/tractoflow/derivatives/tractoflow/v2.2.1/
# /data/pd/qpn/tractoflow/derivatives/tractoflow/v2.2.1/output/tractoflow/ 
## subject outputs, html reports, logs(pipeline citations), dataset_description.json

## write jobs script from input
cat << EOF > ./jobs/qpn_tracto_${SUBJ}.sge
#!/bin/bash

#$ -N qpn_tracto_${SUBJ}
#$ -q all.q
#$ -pe all.pe ${NCORE}
#$ -l h_rt=10:00:00
#$ -l h_vmem=16G 
#$ -e $LOGDIR/${SUBJ}_tractoflow_\$JOB_ID.log
#$ -o $LOGDIR/${SUBJ}_tractoflow_\$JOB_ID.out

## use the right singularity version
export PATH=/opt/bin:\$PATH
singularity --version

## export netwflow paths
export PATH=/data/pd/qpn/tractoflow/bin:\$PATH
nextflow -version

## add jq tool to path w/ alias
alias jq="/data/pd/qpn/tractoflow/bin/jq"

## path to singularity image
SINGULARITY_IMAGE=${SINGULARITY_IMAGE}

## make the tractoflow specific input directory
INPUTDIR=/data/pd/qpn/tractoflow/input/${SUBJ}-\$JOB_ID
mkdir -p \${INPUTDIR}/${SUBJ}

## create and set working directory for job
WORKDIR=/data/pd/qpn/tractoflow/work/${SUBJ}-\$JOB_ID
mkdir \${WORKDIR}
cd \${WORKDIR}

## make the derivatives directories
OUTDIR=${OUTPUT}/${SUBJ}/ses-01
mkdir -p \${OUTDIR}/{anat,dwi,xfm}

## link the input files to scratch directory
ln -s ${BIDSDIR}/anat/${SUBJ}_ses-01_run-1_T1w.nii.gz \${INPUTDIR}/${SUBJ}/t1.nii.gz
ln -s ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.nii.gz \${INPUTDIR}/${SUBJ}/dwi.nii.gz
ln -s ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.bval \${INPUTDIR}/${SUBJ}/bval
ln -s ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.bvec \${INPUTDIR}/${SUBJ}/bvec
#ln -s ${BIDSDIR}/dwi/${SUBJ}_ses-01_dir-PA_run-1_dwi.nii.gz \${INPUTDIR}/${SUBJ}/rev_b0.nii.gz

## the dir-PA image has multiple volumes - not obvious from name
singularity exec --bind ${BIDSDIR},\${INPUTDIR}/${SUBJ} \${SINGULARITY_IMAGE} \\
    scil_image_math.py mean ${BIDSDIR}/dwi/${SUBJ}_ses-01_dir-PA_run-1_dwi.nii.gz \${INPUTDIR}/${SUBJ}/rev_b0.nii.gz
#   mrmath ${BIDSDIR}/dwi/${SUBJ}_ses-01_dir-PA_run-1_dwi.nii.gz mean \${INPUTDIR}/${SUBJ}/rev_b0.nii.gz -axis 3

## flip the bvecs? - maybe necessary, especially if strides are redone
#singularity exec --bind ${BIDSDIR},\${INPUTDIR}/${SUBJ} \${SINGULARITY_IMAGE} \\
#    scil_flip_gradients.py ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.bvec \${INPUTDIR}/${SUBJ}/bvec x --fsl
## FOR QPN, IF STRIDES ARE NOT CHANGED THE BVECS DO NOT NEED TO BE FLIPPED

## convert .nii.gz images with mrconvert to the correct strides?
#singularity exec --bind ${BIDSDIR},\${INPUTDIR}/${SUBJ} \${SINGULARITY_IMAGE} \\
#    mrconvert ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.nii.gz \${INPUTDIR}/${SUBJ}/dwi.nii.gz -strides 1,2,3,4

## add a check of sidecars to ensure *run-1_dwi* has opposite PhaseEncoding of *dir-PA_run-1_dwi* ?
## grep '"PhaseEncodingDirection:"' ${BIDSDIR}/dwi/${SUBJ}_ses-01_run-1_dwi.json
## grep '"PhaseEncodingDirection:"' ${BIDSDIR}/dwi/${SUBJ}_ses-01_dir-PA_run-1_dwi.json
## grep '"PhaseEncodingDirection:"' ${BIDSDIR}/dwi/${SUBJ}_ses-01_dir-AP_run-1_dwi.json

## run the call
nextflow run /data/pd/qpn/tractoflow/bin/tractoflow/main.nf --input \${INPUTDIR} \\
	--dti_shells "0 1000" \\
	--fodf_shells "0 1000" \\
	--sh_order 6 \\
	--processes ${NCORE} \\
	-profile fully_reproducible \\
	-with-singularity \${SINGULARITY_IMAGE} \\
	-with-trace $LOGDIR/${SUBJ}_tractoflow_nf_trace.txt \\
	-with-report $OUTPUT/${SUBJ}_nf_report.html 

##
## move data to bids structure / create sidecars
##

## existing sidecar fields
# echo '{"RawSources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_T1w.nii.gz"], "Type": "Brain", "SkullStripped": false, "keep_dtype": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_FILE_type.json

## copy output files to BIDS derivative structure
cp -rL \${WORKDIR}/results/${SUBJ}/Resample_DWI/${SUBJ}__dwi_resampled.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Eddy_Topup/${SUBJ}__bval_eddy \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.bval
cp -rL \${WORKDIR}/results/${SUBJ}/Eddy_Topup/${SUBJ}__dwi_eddy_corrected.bvec \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.bvec
cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__t1_mask_warped.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-brain_mask.nii.gz
#cp -rL \${WORKDIR}/results/${SUBJ}/Eddy_Topup/${SUBJ}__b0_bet_mask.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-brain_mask.nii.gz
echo '{"RawSources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_dwi.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.json
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_T1w.nii.gz"], "Type": "Brain"}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_desc-brain_mask.json
## IF revb0.nii.gz IS NOT PART OF THE INPUT TOPUP IS NOT PERFORMED - THE FINAL FILES WILL BE IN A DIFFERENT FOLDER

cp -rL \${WORKDIR}/results/${SUBJ}/Crop_T1/${SUBJ}__t1_bet_cropped.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_T1w.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Crop_T1/${SUBJ}__t1_bet_mask_cropped.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_mask.nii.gz
echo '{"RawSources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_T1w.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_T1w.json
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_T1w.nii.gz"], "Type": "Brain"}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_mask.json

cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__t1_warped.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__t1_mask_warped.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_desc-brain_mask.nii.gz
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_desc-preprocessed_T1w.nii.gz"], "masked": false}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.json
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.nii.gz"], "Type": "Brain"}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_desc-brain_mask.json

cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__output0GenericAffine.mat \${OUTDIR}/xfm/${SUBJ}_ses-1_run-1_desc-tractoflow_from-T1w_to-dwi_0GenericAffine.txt
cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__output1Warp.nii.gz \${OUTDIR}/xfm/${SUBJ}_ses-1_run-1_desc-tractoflow_from-T1w_to-dwi_1Warp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Register_T1/${SUBJ}__output1InverseWarp.nii.gz \${OUTDIR}/xfm/${SUBJ}_ses-1_run-1_desc-tractoflow_from-dwi_to-T1w_1InverseWarp.nii.gz
echo '{"Type": ["rigid", "displacementfield"], "Multiplexed": [true, false], "Software": "ANTs", "Invertible": true, "Sources": {"FromFile": "${SUBJ}/anat/${SUBJ}_ses-1_run-1_T1w.nii.gz", "ToFile": "${SUBJ}/dwi/${SUBJ}_ses-1_run-1_preprocessed_dwi.nii.gz"}}' | jq . > \${OUTDIR}/xfm/${SUBJ}_ses-1_run-1_desc-tractoflow_from-T1w_to_dwi.json

cp -rL \${WORKDIR}/results/${SUBJ}/Segment_Tissues/${SUBJ}__map_csf.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Segment_Tissues/${SUBJ}__map_gm.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Segment_Tissues/${SUBJ}__map_wm.nii.gz \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label-WM_probseg.nii.gz

echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.json
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.json
echo '{"Sources": ["${SUBJ}/ses-01/anat/${SUBJ}_ses-1_run-1_space-dwi_T1w.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/anat/${SUBJ}_ses-1_run-1_space-dwi_label_WM_probseg.json

cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__tensor.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__rgb.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-rgb_mdp.nii.gz

echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.nii.gz"], "Mask": "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_desc-brain_mask.nii.gz", "Model": "Diffusion Tensor", "OrientationRepresentation": "param", "ReferenceAxes": "xyz", "Parameters": {"Fit": "ols", "OutlierRejection": false}}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-rgb_mdp.json

cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__fa.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-fa_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__md.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-md_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__rd.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-rd_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__ad.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-ad_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/DTI_Metrics/${SUBJ}__ga.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-ga_mdp.nii.gz

echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-fa_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-md_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-rd_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-ad_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-tensor_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tensor_param-ga_mdp.json

cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__fodf.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__peaks.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-peaks_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/Compute_FRF/${SUBJ}__frf.txt \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-frf_response.txt

echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_desc-preprocessed_dwi.nii.gz", ${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_desc-frf_response.txt, ${SUBJ}/ses-1/dwi/${SUBJ}_ses-1_run-1_desc-brain_mask.nii.gz], "Model": "Constrained Spherical Deconvolution", "Parameters": {"SphericalHarmonicBasis": "mrtrix3", "NonnegativityConstraint": "hard"}, "OrientationRepresentation": "sh", "ReferenceAxes": "xyz", "Tissue": "brain"}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_desc-model_fodf.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-peaks_mdp.json

cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__afd_max.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdmax_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__afd_sum.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdsum_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__afd_total.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdtotal_mdp.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/FODF_Metrics/${SUBJ}__nufo.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-nufo_mdp.nii.gz

echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdsum_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdmax_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-afdtotal_mdp.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-csd_param-nufo_mdp.json

cp -rL \${WORKDIR}/results/${SUBJ}/PFT_Seeding_Mask/${SUBJ}__pft_seeding_mask.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-seeding_mask.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/PFT_Tracking_Maps/${SUBJ}__interface.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-interface_mask.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/PFT_Tracking_Maps/${SUBJ}__map_exclude.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-exlucde_probmap.nii.gz
cp -rL \${WORKDIR}/results/${SUBJ}/PFT_Tracking_Maps/${SUBJ}__map_include.nii.gz \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-include_probmap.nii.gz

echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-WM_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-seeding_mask.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-WM_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-interface_mask.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-WM_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-exclude_probmap.json
echo '{"Sources": ["${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-CSF_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-WM_probseg.nii.gz", "${SUBJ}/ses-01/dwi/${SUBJ}_ses-1_run-1_space-dwi_label-GM_probseg.nii.gz"], "masked": true}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-include_probmap.json

cp -rL \${WORKDIR}/results/${SUBJ}/PFT_Tracking/${SUBJ}__pft_tracking_prob_wm_seed_0.trk \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-wholebrain.trk

echo '{"TrackingType": "pft", "Sources": {"Model": "${SUBJ}/dwi/${SUBJ}_ses-1_run-1_model-csd_desc-fodf_model.nii.gz", "SeedMaps": ["${SUBJ}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-seeding_mask.nii.gz"], "IncludeMaps": ["${SUBJ}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-include_probmap.nii.gz"], "ExcludeMaps": ["${SUBJ}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-exclude_probmap.nii.gz"], "InterfaceMaps": "${SUBJ}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-interface_mask.nii.gz"}, "TrackingMode": "prob", "StepSize": 0.50, "Theta": 20, "MinLength": 20, "MaxLength": 200, "shBasis": "descoteaux07", "sfThres": 0.10, "sfInit": 0.50, "nParticles": 15, "nBack": 2, "nForward": 1, "npv": 10, "compress": 0.20}' | jq . > \${OUTDIR}/dwi/${SUBJ}_ses-1_run-1_model-tracking_desc-wholebrain.json

## remove INPUTDIR links and job working directory
rm -rf \${INPUTDIR}
rm -rf \${WORKDIR} ## this removes all the original tractoflow outputs

EOF
