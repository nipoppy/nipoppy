# coding=utf-8

"""
This script is used to run functional connectivity (FC) assessment
using Nilearn on a single functional nifti file.

The script extracts time series from the functional
file using a given list of brain atlases.
"""

import argparse
import sys
from copy import deepcopy
from pathlib import Path

# try importing bids and if it fails, give instructions to install bids
try:
    from bids.layout import parse_file_entities
except ImportError:
    sys.exit("pybids not found. Please install pybids by running: pip install pybids")


# try importing nilearn and if it fails, give instructions to install nilearn
try:
    from nilearn import datasets
    from nilearn.interfaces.fmriprep import load_confounds
    from nilearn.maskers import NiftiLabelsMasker
except ImportError:
    sys.exit(
        "nilearn not found." " Please install nilearn by running: pip install nilearn"
    )


# try importing numpy and if it fails, give instructions to install numpy
try:
    import numpy as np
except ImportError:
    sys.exit("numpy not found. Please install numpy by running: pip install numpy")

# try importing sklearn and if it fails, give instructions to install sklearn
try:
    import sklearn
except ImportError:
    sys.exit(
        "scikit-learn not found."
        " Please install scikit-learn by running: pip install scikit-learn"
    )

import os
import warnings

warnings.simplefilter("ignore")


def extract_timeseries(func_file, brain_atlas, confound_strategy):
    """
    Extract timeseries from a given functional file using a given brain atlas.

    func_file:
        path to the nifti file containing the functional data
        This path should be in the fmriprep output directory
        The functional data is assumed to be preprocessed by fmriprep and
        transformed to MNI space
    confound_strategy:
        'none': no confound regression
        'no_motion': confound regression with no motion parameters
        'no_motion_no_gsr': confound regression with no motion parameters and
            no global signal regression
            if confound_strategy is no_motion or no_motion_no_gsr, the associated
            confound files should be in the same directory as func_file
    brain_atlas:
        for now only supports:
        'schaefer_100', 'schaefer_200', 'schaefer_300', 'schaefer_400',
        'schaefer_500', 'schaefer_600', 'schaefer_800', 'schaefer_1000'
        'DKT'
        if brain_atlas is not 'schaefer', then it is assumed to be dkt_atlas file
    """
    # Load Atlas
    # schaefer
    if "schaefer" in brain_atlas:
        n_rois = int(brain_atlas.removeprefix("schaefer_"))
        parc = datasets.fetch_atlas_schaefer_2018(n_rois=n_rois)
        atlas_filename = parc.maps
        labels = parc.labels
        # The list of labels does not contain ‘Background’ by default.
        # To have proper indexing, you should either manually add ‘Background’
        # to the list of labels:
        # Prepend background label
        labels = np.insert(labels, 0, "Background")
        # create the masker for extracting time series
        masker = NiftiLabelsMasker(labels_img=atlas_filename, standardize=True)
    # DKT
    else:
        atlas_filename = brain_atlas
        labels = None
        # create the masker for extracting time series
        # if file was not found, raise error
        if not os.path.isfile(atlas_filename):
            raise ValueError("atlas_filename not found")
        masker = NiftiLabelsMasker(labels_img=atlas_filename, standardize=True)

    # extract the timeseries
    if confound_strategy == "none":
        time_series = masker.fit_transform(func_file)
    elif confound_strategy == "no_motion":
        confounds, sample_mask = load_confounds(
            func_file,
            strategy=["high_pass", "motion", "wm_csf"],
            motion="basic",
            wm_csf="basic",
        )
        time_series = masker.fit_transform(
            func_file, confounds=confounds, sample_mask=sample_mask
        )
    elif confound_strategy == "no_motion_no_gsr":
        confounds, sample_mask = load_confounds(
            func_file,
            strategy=["high_pass", "motion", "wm_csf", "global_signal"],
            motion="basic",
            wm_csf="basic",
            global_signal="basic",
        )
        time_series = masker.fit_transform(
            func_file, confounds=confounds, sample_mask=sample_mask
        )
    else:
        raise ValueError("confound_strategy not recognized")

    if labels is None:
        labels = [f"region_{i}" for i in range(time_series.shape[1])]
        labels = np.insert(labels, 0, "Background")

    return time_series, labels


def assess_FC(time_series, labels, metric_list=["correlation"]):
    """
    Assess functional connectivity using Nilearn.

    metric_list:
        'correlation'
        'precision'
    """
    # output dictionary
    FC = {}

    FC["roi_labels"] = labels[
        1:
    ]  # Be careful that the indexing should be offset by one

    # functional connectivity assessment
    # correlation
    if "correlation" in metric_list:
        from nilearn.connectome import ConnectivityMeasure

        correlation_measure = ConnectivityMeasure(kind="correlation")
        correlation_matrix = correlation_measure.fit_transform([time_series])[0]
        FC["correlation"] = deepcopy(correlation_matrix)

    # sparse inverse covariance
    if "precision" in metric_list:
        try:
            from sklearn.covariance import GraphicalLassoCV
        except ImportError:
            # for Scitkit-Learn < v0.20.0
            from sklearn.covariance import GraphLassoCV as GraphicalLassoCV

        estimator = GraphicalLassoCV()
        estimator.fit(time_series)

        # The covariance can be found at estimator.covariance_
        covariance_mat = estimator.covariance_
        FC["covariance"] = deepcopy(covariance_mat)

        precision_mat = -estimator.precision_
        FC["precision"] = deepcopy(precision_mat)

    return FC


def run(
    func_file: str,
    brain_atlas_list: list,
    confound_strategy: str,
    metric_list: list,
    dkt_file: str,
    output_dir: str,
):
    """Assess functional connectivity using Nilearn."""
    # func_file has a form of
    # f"{fmriprep_dir}/{participant_id}/ses-{session_id}/func/
    # {participant_id}_ses-{session_id}_{task}_{run}_{space}_desc-preproc_bold.nii.gz"
    func_file_name = Path(func_file).name

    # sanity check
    assert (
        "desc-preproc_bold.nii.gz" in func_file_name
    ), f"func_file_name: {func_file_name} does not contain 'desc-preproc_bold.nii.gz'"

    file_entities = parse_file_entities(func_file)
    participant_id = f"sub-{file_entities.get('subject')}"
    session_id = file_entities.get("session")
    extension = file_entities.get("extension")

    print(f"Running FC assessment for participant: {participant_id}...")
    print("-" * 50)

    # check if the func file exists
    if not os.path.exists(func_file):
        raise FileNotFoundError(f"func file not found: {func_file}")

    try:
        for brain_atlas in brain_atlas_list:
            print("******** running " + brain_atlas)
            # extract time series
            if "schaefer" in brain_atlas:
                time_series, labels = extract_timeseries(
                    func_file, brain_atlas, confound_strategy
                )
            elif brain_atlas == "DKT":
                if dkt_file is None:
                    print("DKT atlas file not provided")
                    continue
                if not os.path.exists(dkt_file):
                    print(f"DKT atlas file not found: {dkt_file}")
                    continue
                time_series, labels = extract_timeseries(
                    func_file, dkt_file, confound_strategy
                )
            else:
                print(f"Brain atlas not recognized: {brain_atlas}")
                continue

            # assess FC
            FC = assess_FC(time_series, labels, metric_list=metric_list)

            # save output
            if session_id is None:
                folder = f"{output_dir}/FC/output/{participant_id}/"
            else:
                folder = f"{output_dir}/FC/output/{participant_id}/ses-{session_id}/"
            if not os.path.exists(folder):
                os.makedirs(folder)

            # if the brain atlas has "_" remove it
            brain_atlas_name = brain_atlas.replace("_", "")
            out_file_name = (
                f"{func_file_name.removesuffix(extension)}"
                f"_atlas-{brain_atlas_name}_FC.npy"
            )
            np.save(f"{folder}/{out_file_name}", FC)
            print(
                "Successfully completed FC assessment for participant: "
                f"{participant_id}"
            )
    except Exception as e:
        sys.exit(
            f"FC assessment for participant {participant_id} "
            f"failed with exceptions: {e}"
        )

    print("-" * 75)
    print("")


if __name__ == "__main__":
    # argparse
    HELPTEXT = """
    Script to run FC assessment
    """

    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument(
        "--func_file", type=str, required=True, help="path to the BOLD nifti file"
    )
    # example: --brain_atlas_list "schaefer_100" "schaefer_200"
    parser.add_argument(
        "--brain_atlas_list",
        type=str,
        choices=[
            "schaefer_100",
            "schaefer_200",
            "schaefer_300",
            "schaefer_400",
            "schaefer_500",
            "schaefer_600",
            "schaefer_800",
            "schaefer_1000",
            "DKT",
        ],
        nargs="+",  # at least one atlas required
        default=[
            "schaefer_100",
            "schaefer_200",
            "schaefer_300",
            "schaefer_400",
            "schaefer_500",
            "schaefer_600",
            "schaefer_800",
            "schaefer_1000",
        ],
        help=(
            "list of brain atlases to use for FC assessment."
            " Default is all schaefer resolutions"
        ),
    )
    parser.add_argument(
        "--confound_strategy",
        type=str,
        choices=[
            "none",
            "no_motion",
            "no_motion_no_gsr",
        ],
        default="no_motion",
        help="confound strategy for FC assessment. Default is no_motion",
    )
    parser.add_argument(
        "--metric_list",
        type=str,
        choices=[
            "correlation",
            "precision",
        ],
        nargs="+",  # at least one atlas required
        default=["correlation"],
        help="list of metrics to use for FC assessment. Default is correlation",
    )
    parser.add_argument(
        "--dkt_file", type=str, default=None, help="path to the DKT atlas file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="output directory to save FC results",
    )

    args = parser.parse_args()

    func_file = args.func_file
    brain_atlas_list = args.brain_atlas_list
    confound_strategy = args.confound_strategy
    metric_list = args.metric_list
    dkt_file = args.dkt_file
    output_dir = args.output_dir

    # run the analysis
    run(
        func_file,
        brain_atlas_list,
        confound_strategy,
        metric_list,
        dkt_file,
        output_dir,
    )
