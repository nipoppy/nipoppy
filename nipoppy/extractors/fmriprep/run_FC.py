import argparse
from copy import deepcopy
import json
import nipoppy.workflow.logger as my_logger
import logging
from nilearn.maskers import NiftiLabelsMasker
from nilearn.interfaces.fmriprep import load_confounds
from nilearn import datasets
import numpy as np
import os
import warnings

warnings.simplefilter('ignore')


def extract_timeseries(func_file, brain_atlas, confound_strategy):
	""" 
	Extract timeseries from a given functional file using a given brain atlas 
	func_file:
		path to the nifti file containing the functional data
		This path should be in the fmriprep output directory
		The functional data is assumed to be preprocessed by fmriprep and transformed to MNI space
	confound_strategy:
		'none': no confound regression
		'no_motion': confound regression with no motion parameters
		'no_motion_no_gsr': confound regression with no motion parameters and no global signal regression
		if confound_strategy is no_motion or no_motion_no_gsr, the associated confound files should be 
			in the same directory as func_file
	brain_atlas:
		for now only supports:
		'schaefer_100', 'schaefer_200', 'schaefer_300', 'schaefer_400', 'schaefer_500', 'schaefer_600', 'schaefer_800', 'schaefer_1000'
		'DKT'
		if brain_atlas is not 'schaefer', then it is assumed to be dkt_atlas file
	"""
	### Load Atlas
	## schaefer
	if 'schaefer' in brain_atlas:
		n_rois = int(brain_atlas[brain_atlas.find('schaefer')+9:])
		parc = datasets.fetch_atlas_schaefer_2018(n_rois=n_rois)
		atlas_filename = parc.maps
		labels = parc.labels
		# The list of labels does not contain ‘Background’ by default. 
		# To have proper indexing, you should either manually add ‘Background’ to the list of labels:
		# Prepend background label
		labels = np.insert(labels, 0, 'Background')
		# create the masker for extracting time series
		masker = NiftiLabelsMasker(labels_img=atlas_filename, standardize=True)
	## DKT
	else:
		atlas_filename = brain_atlas
		labels = None
		# create the masker for extracting time series
		# if file was not found, raise error
		if not os.path.isfile(atlas_filename):
			raise ValueError('atlas_filename not found')
		masker = NiftiLabelsMasker(labels_img=atlas_filename, standardize=True)

	### extract the timeseries
	if confound_strategy=='none':
		time_series = masker.fit_transform(func_file)
	elif confound_strategy=='no_motion':
		confounds, sample_mask = load_confounds(
				func_file,
				strategy=["high_pass", "motion", "wm_csf"],
				motion="basic", wm_csf="basic"
		)
		time_series = masker.fit_transform(
				func_file,
				confounds=confounds,
				sample_mask=sample_mask
		)
	elif confound_strategy=='no_motion_no_gsr':
		confounds, sample_mask = load_confounds(
				func_file,
				strategy=["high_pass", "motion", "wm_csf", "global_signal"],
				motion="basic", wm_csf="basic", global_signal="basic"
		)
		time_series = masker.fit_transform(
				func_file,
				confounds=confounds,
				sample_mask=sample_mask
		)
	else:
		raise ValueError('confound_strategy not recognized')

	if labels is None:
		labels = ['region_'+str(i) for i in range(time_series.shape[1])]
		labels = np.insert(labels, 0, 'Background')

	return time_series, labels


def assess_FC(time_series, labels, metric_list=['correlation']):
	"""
	Assess functional connectivity using Nilearn
	metric_list:
		'correlation'
		'precision'
	"""
	### output dictionary
	FC = {}

	FC['roi_labels'] = labels[1:] # Be careful that the indexing should be offset by one

	### functional connectivity assessment
	## correlation
	if 'correlation' in metric_list:
		from nilearn.connectome import ConnectivityMeasure
		correlation_measure = ConnectivityMeasure(kind='correlation')
		correlation_matrix = correlation_measure.fit_transform([time_series])[0]
		FC['correlation'] = deepcopy(correlation_matrix)

	## sparse inverse covariance 
	if 'precision' in metric_list:
		try:
				from sklearn.covariance import GraphicalLassoCV
		except ImportError:
		# for Scitkit-Learn < v0.20.0
				from sklearn.covariance import GraphLassoCV as GraphicalLassoCV

		estimator = GraphicalLassoCV()
		estimator.fit(time_series)

		# The covariance can be found at estimator.covariance_
		covariance_mat = estimator.covariance_
		FC['covariance'] = deepcopy(covariance_mat)

		precision_mat = -estimator.precision_
		FC['precision'] = deepcopy(precision_mat)

	return FC

def run_FC(
	participant_id: str,
	session_id: str,
	fmriprep_dir,
	DKT_dir,
	FC_dir,
	brain_atlas_list,
	confound_strategy,
	metric_list,
	task,
	run,
	space,
	logger: logging.Logger,
):
	""" Assess functional connectivity using Nilearn"""
	
	logger.info("Running FC assessment...")
	logger.info("-"*50)

	func_file = f"{fmriprep_dir}/{participant_id}/ses-{session_id}/func/{participant_id}_ses-{session_id}_{task}_{run}_{space}_desc-preproc_bold.nii.gz"
	# check if the func file exists
	if not os.path.exists(func_file):
		logger.error(f"func file not found: {func_file}")
		logger.error(f"Skipping participant: {participant_id}")
		return
	
	try:
		for brain_atlas in brain_atlas_list:
			logger.info('******** running ' + brain_atlas)
			### extract time series
			if 'schaefer' in brain_atlas:
				time_series, labels = extract_timeseries(func_file, brain_atlas, confound_strategy)
			elif brain_atlas=='DKT':
				dkt_atlas = f"{DKT_dir}/{participant_id}/ses-{session_id}/anat/{participant_id}_ses-{session_id}_run-{run}_{space[:-6]}_atlas-DKTatlas+aseg_dseg.nii.gz" # space[:-6] removes the '_res2' suffix
				time_series, labels = extract_timeseries(func_file, dkt_atlas, confound_strategy)
			else:
				raise ValueError('brain_atlas not supported')

			### assess FC
			FC = assess_FC(time_series, labels, metric_list=metric_list)

			## save output 
			folder = f"{FC_dir}/output/{participant_id}/ses-{session_id}/"
			if not os.path.exists(folder):
				os.makedirs(folder)
			np.save(f"{folder}/{participant_id}_ses-{session_id}_{task}_{space}_FC_{brain_atlas}.npy", FC)
			logger.info(f"Successfully completed FC assessment for participant: {participant_id}")
	except Exception as e:
		logger.error(f"FC assessment failed with exceptions: {e}")
		logger.error(f"Failed participant: {participant_id}")

	logger.info("-"*75)
	logger.info("")


def run(participant_id: str,
	global_configs,
	FC_configs,
	session_id: str,
	output_dir: str,
	logger=None
):
	""" Runs fmriprep command
	"""
	DATASET_ROOT = global_configs["DATASET_ROOT"]
	FMRIPREP_VERSION = global_configs["PROC_PIPELINES"]["fmriprep"]["VERSION"]

	confound_strategy = FC_configs["confound_strategy"]
	metric_list = FC_configs["metric_list"]
	brain_atlas_list = FC_configs["brain_atlas_list"]
	task = FC_configs["task"]
	run = FC_configs["run"]
	space = FC_configs["space"]

	if metric_list is None:
		metric_list = ['correlation']
	if brain_atlas_list is None:
		brain_atlas_list = [
			'schaefer_100', 'schaefer_200',
			'schaefer_300', 'schaefer_400',
			'schaefer_500', 'schaefer_600',
			'schaefer_800', 'schaefer_1000'
		]
	if confound_strategy is None:
		confound_strategy = 'none'

	log_dir = f"{DATASET_ROOT}/scratch/logs/"

	if logger is None:
		log_file = f"{log_dir}/FC.log"
		logger = my_logger.get_logger(log_file)

	logger.info("-"*75)
	logger.info(f"Using DATASET_ROOT: {DATASET_ROOT}")
	logger.info(f"Using participant_id: {participant_id}, session_id:{session_id}")

	if output_dir is None:
		output_dir = f"{DATASET_ROOT}/derivatives/"

	fmriprep_dir = f"{DATASET_ROOT}/derivatives/fmriprep/v{FMRIPREP_VERSION}/output"
	DKT_dir = f"{DATASET_ROOT}/derivatives/networks/0.9.0/output"
	FC_dir = f"{output_dir}/FC"

	# check if the func/ exists in fmriprep_dir
	func_dir = f"{fmriprep_dir}/{participant_id}/ses-{session_id}/func/"
	if not os.path.exists(func_dir):
		logger.error(
			f"func data not found: {func_dir}"
		)
		logger.error(f"Skipping participant: {participant_id}")
		return

	# assess FC
	run_FC(
		participant_id,
		session_id,
		fmriprep_dir,
		DKT_dir,
		FC_dir,
		brain_atlas_list,
		confound_strategy,
		metric_list,
		task,
		run,
		space,
		logger,
	)
    

if __name__ == '__main__':
	# argparse
	HELPTEXT = """
	Script to run FC assessment 
	"""

	parser = argparse.ArgumentParser(description=HELPTEXT)

	parser.add_argument('--global_config', type=str, help='path to global configs for a given nipoppy dataset')
	parser.add_argument('--FC_config', type=str, help='path to FC assessment configs for a given nipoppy dataset')
	parser.add_argument('--participant_id', type=str, help='participant id')
	parser.add_argument('--session_id', type=str, help='session id for the participant')
	parser.add_argument('--output_dir', type=str, default=None, 
						help='specify custom output dir (if None --> <DATASET_ROOT>/derivatives)')

	args = parser.parse_args()

	global_config_file = args.global_config
	FC_config_file = args.FC_config
	participant_id = args.participant_id
	session_id = args.session_id
	output_dir = args.output_dir # Needed on BIC (QPN) due to weird permissions issues with mkdir

	# Read global configs
	with open(global_config_file, 'r') as f:
		global_configs = json.load(f)

	# Read FC configs
	with open(FC_config_file, 'r') as f:
		FC_configs = json.load(f)

	run(participant_id, global_configs, FC_configs, session_id, output_dir)
