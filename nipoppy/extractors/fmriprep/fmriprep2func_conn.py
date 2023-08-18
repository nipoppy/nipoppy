from nilearn.maskers import NiftiLabelsMasker, NiftiSpheresMasker
from nilearn.interfaces.fmriprep import load_confounds
from nilearn import datasets
from nilearn import plotting
import numpy as np
from copy import deepcopy
import os
import warnings

warnings.simplefilter('ignore')


### paths to files
# root = '/Users/mte/Documents/McGill/JB/QPN/data/'
# output_root = '/Users/mte/Documents/McGill/JB/QPN/FC_output/'

root = '../../../../pd/qpn/derivatives/fmriprep/v20.2.7/fmriprep/'
output_root = '../outputs/FC_outputs/'

### parameters

reorder_conn_mat = True
visualize = False
brain_atlas = 'schaefer' # schaefer or seitzman
confound_strategy = 'no_motion_no_gsr' # no_motion or no_motion_no_gsr

test_output = False

### Load Atlas

## schaefer
if brain_atlas=='schaefer':
      parc = datasets.fetch_atlas_schaefer_2018(n_rois=100)
      atlas_filename = parc.maps
      labels = parc.labels
      # The list of labels does not contain ‘Background’ by default. 
      # To have proper indexing, you should either manually add ‘Background’ to the list of labels:
      # Prepend background label
      labels = np.insert(labels, 0, 'Background')
      # create the masker for extracting time series
      masker = NiftiLabelsMasker(labels_img=atlas_filename, standardize=True)
## seitzman
if brain_atlas=='seitzman':
      parc = datasets.fetch_coords_seitzman_2018()
      atlas_filename = parc['rois']
      radius = parc['radius']
      labels = parc['regions']
      # create the masker for extracting time series
      masker = NiftiSpheresMasker(seeds=atlas_filename, radius=radius, standardize=True)

### Load Subjects
ALL_SUBJECTS = os.listdir(root)
ALL_SUBJECTS = [i for i in ALL_SUBJECTS if ('sub' in i) and (not '.html' in i)]
ALL_SUBJECTS.sort()
print('*** '+ str(len(ALL_SUBJECTS)) + ' subjects were found.')
for subj in ALL_SUBJECTS:
      print('*** running '+subj)
      ### output dictionary
      FC = {}
      
      ### functional data
      bold = root + subj + '/ses-01/func/'+ subj +'_ses-01_task-rest_run-1_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz'

      ### Confounds

      if confound_strategy=='no_motion':
            confounds_simple, sample_mask = load_confounds(
                  bold,
                  strategy=["high_pass", "motion", "wm_csf"],
                  motion="basic", wm_csf="basic"
                  )
      if confound_strategy=='no_motion_no_gsr':
            confounds_minimal_no_gsr, sample_mask = load_confounds(
                  bold,
                  strategy=["high_pass", "motion", "wm_csf", "global_signal"],
                  motion="basic", wm_csf="basic", global_signal="basic"
                  )

      ### extract the timeseries
      time_series = masker.fit_transform(bold,
                              confounds=confounds_minimal_no_gsr,
                              sample_mask=sample_mask)

      FC['roi_labels'] = labels[1:] # Be careful that the indexing should be offset by one

      ### functional connectivity assessment
      ## correlation

      from nilearn.connectome import ConnectivityMeasure
      correlation_measure = ConnectivityMeasure(kind='correlation')
      correlation_matrix = correlation_measure.fit_transform([time_series])[0]
      FC['correlation'] = deepcopy(correlation_matrix)

      # Plot the correlation matrix

      if visualize:
            # Make a large figure
            # Mask the main diagonal for visualization:
            np.fill_diagonal(correlation_matrix, 0)
            # The labels we have start with the background (0), hence we skip the
            # first label
            # matrices are ordered for block-like representation
            plotting.plot_matrix(correlation_matrix, figure=(10, 8), labels=labels[1:],
                              vmax=1, vmin=-1, title="Correlation Confounds regressed",
                              reorder=reorder_conn_mat)

      ## sparse inverse covariance 
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
      if visualize:
            np.fill_diagonal(covariance_mat, 0)
            plotting.plot_matrix(covariance_mat, labels=labels[1:],
                              figure=(9, 7), vmax=1, vmin=-1,
                              title='Covariance', reorder=reorder_conn_mat)

      precision_mat = -estimator.precision_
      FC['precision'] = deepcopy(precision_mat)
      if visualize:
            np.fill_diagonal(precision_mat, 0)
            plotting.plot_matrix(precision_mat, labels=labels[1:],
                              figure=(9, 7), vmax=1, vmin=-1,
                              title='Sparse inverse covariance', reorder=reorder_conn_mat)
      if visualize:
            plotting.show()

      ### save output 
      np.save(output_root+subj+'_FC_output.npy', FC) 

print('*** FC measurement finished successfully.')

### test outputs
if test_output:
      # calc average static FC

      metric = 'precision' # correlation , covariance , precision 
      dir = './FC_outputs/'

      ALL_RECORDS = os.listdir(dir)
      ALL_RECORDS = [i for i in ALL_RECORDS if 'FC_output' in i]
      ALL_RECORDS.sort()
      print(str(len(ALL_RECORDS))+' subjects were found.')

      FC_all = list()
      FC_MNI = list()
      FC_PD = list()
      for subj in ALL_RECORDS:
            FC = np.load(dir+subj,allow_pickle='TRUE').item()
            FC_all.append(FC[metric])
            if 'MNI' in subj:
                  FC_MNI.append(FC[metric])
            if 'PD' in subj:
                  FC_PD.append(FC[metric])
      print(str(len(FC_MNI))+' MNI subjects were found.')
      print(str(len(FC_PD))+' PD subjects were found.')
      avg_FC = np.mean(np.array(FC_all), axis=0)
      avg_FC_MNI = np.mean(np.array(FC_MNI), axis=0)
      avg_FC_PD = np.mean(np.array(FC_PD), axis=0)
      np.fill_diagonal(avg_FC, 0)
      plotting.plot_matrix(avg_FC, labels=FC['roi_labels'],
                  figure=(9, 7), vmax=1, vmin=-1,
                  title=metric+' ALL', reorder=False)
      np.fill_diagonal(avg_FC_MNI, 0)
      plotting.plot_matrix(avg_FC_MNI, labels=FC['roi_labels'],
                  figure=(9, 7), vmax=1, vmin=-1,
                  title=metric+' MNI', reorder=False)
      np.fill_diagonal(avg_FC_PD, 0)
      plotting.plot_matrix(avg_FC_PD, labels=FC['roi_labels'],
                  figure=(9, 7), vmax=1, vmin=-1,
                  title=metric+' PD', reorder=False)
      plotting.show()