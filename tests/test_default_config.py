"""Test that all supported pipelines can run successfully in simulate mode."""

import warnings
from pathlib import Path
from shutil import copytree
from typing import Type

import pytest
import pytest_mock
from boutiques import bosh

from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig, BidsPipelineConfig
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME, PipelineTypeEnum
from nipoppy.layout import DatasetLayout
from nipoppy.utils import (
    DPATH_SAMPLE_PIPELINES,
    FPATH_SAMPLE_CONFIG,
    TEMPLATE_REPLACE_PATTERN,
    load_json,
)
from nipoppy.workflows import (
    BidsConversionRunner,
    ExtractionRunner,
    PipelineRunner,
    PipelineTracker,
)

from .conftest import create_empty_dataset, prepare_dataset


@pytest.fixture()
def single_subject_dataset(
    tmp_path: Path, mocker: pytest_mock.MockerFixture
) -> DatasetLayout:
    dataset_root = tmp_path / "my_dataset"
    participant_id = "01"
    session_id = "01"
    container_command = "apptainer"
    substitutions = {
        "[[HEUDICONV_HEURISTIC_FILE]]": str(tmp_path / "heuristic.py"),
        "[[DCM2BIDS_CONFIG_FILE]]": str(tmp_path / "dcm2bids_config.json"),
        "[[FREESURFER_LICENSE_FILE]]": str(tmp_path / "freesurfer_license.txt"),
        "[[TEMPLATEFLOW_HOME]]": str(tmp_path / "templateflow"),
    }

    participants_and_sessions = {participant_id: [session_id]}

    layout = DatasetLayout(dataset_root)
    create_empty_dataset(dataset_root)
    copytree(DPATH_SAMPLE_PIPELINES, layout.dpath_pipelines, dirs_exist_ok=True)

    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=layout.dpath_bids,
    )
    manifest.save_with_backup(layout.fpath_manifest)

    config = Config.load(FPATH_SAMPLE_CONFIG, apply_substitutions=False)
    config.SUBSTITUTIONS = substitutions
    config.save(layout.fpath_config)

    for placeholder, fpath in substitutions.items():
        if "FILE" in placeholder:
            Path(fpath).touch()

    # patch so that the test runs even if the command is not available
    mocker.patch(
        "nipoppy.config.container.check_container_command",
        return_value=container_command,
    )

    return layout, participant_id, session_id


@pytest.fixture()
def bids_pipeline_configs() -> list[BidsPipelineConfig]:
    return get_pipeline_configs(
        DPATH_SAMPLE_PIPELINES
        / DatasetLayout.pipeline_type_to_dname_map[PipelineTypeEnum.BIDSIFICATION],
        BidsPipelineConfig,
    )


def get_pipeline_configs(dpath: Path, pipeline_config_class: Type[BasePipelineConfig]):
    return [
        pipeline_config_class(**load_json(fpath_config))
        for fpath_config in dpath.glob(f"*/{DatasetLayout.fname_pipeline_config}")
    ]


def get_fpaths_descriptors() -> list[str]:
    return [
        str(fpath) for fpath in Path(DPATH_SAMPLE_PIPELINES).glob("**/descriptor*.json")
    ]


def get_fmriprep_output_paths(
    participant_id, session_id, pipeline_version=None
) -> list[str]:
    fpaths = [
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_desc-preproc_T1w.json",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_desc-preproc_T1w.nii.gz",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_desc-brain_mask.json",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_desc-brain_mask.nii.gz",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_dseg.nii.gz",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_label-CSF_probseg.nii.gz",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_label-GM_probseg.nii.gz",  # noqa E501
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_label-WM_probseg.nii.gz",  # noqa E501
    ]

    if pipeline_version == "20.2.7":
        fpaths = [f"fmriprep/{fpath}" for fpath in fpaths]

    return fpaths


def get_mriqc_output_paths(
    participant_id, session_id, pipeline_version=None
) -> list[str]:
    return [
        f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_T1w.json",  # noqa E501
        f"sub-{participant_id}_ses-{session_id}_T1w.html",
    ]


def get_qsiprep_output_paths(
    participant_id, session_id, pipeline_version=None
) -> list[str]:
    if pipeline_version == "0.23.0":
        fpaths = [
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_desc-preproc_T1w.json",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_desc-preproc_T1w.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_desc-brain_mask.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_from-T1wNative_to-T1wACPC_mode-image_xfm.mat",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_desc-aseg_dseg.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_from-T1wACPC_to-T1wNative_mode-image_xfm.mat",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/anat/sub-{participant_id}_dseg.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-preproc_dwi.b",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_confounds.tsv",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-brain_mask.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_desc-SliceQC_dwi.json",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_dwiref.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_desc-ImageQC_dwi.csv",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-preproc_dwi.b_table.txt",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-preproc_dwi.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-preproc_dwi.bvec",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-eddy_cnr.nii.gz",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-T1w_desc-preproc_dwi.bval",  # noqa E501
            f"ses-{session_id}/sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_from-orig_to-T1w_mode-image_xfm.txt",  # noqa E501
        ]
    elif pipeline_version == "0.24.0":
        fpaths = [
            f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-brain_mask.nii.gz",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_T1w.nii.gz",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_T1w.json",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_from-ACPC_to-MNI152NLin2009cAsym_mode-image_xfm.h5",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/anat/sub-{participant_id}_ses-{session_id}_from-MNI152NLin2009cAsym_to-ACPC_mode-image_xfm.h5",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-brain_mask.nii.gz",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_dwi.nii.gz",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_dwi.json",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_dwi.b",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_dwi.bval",  # noqa E501
            f"sub-{participant_id}/ses-{session_id}/dwi/sub-{participant_id}_ses-{session_id}_space-ACPC_desc-preproc_dwi.bvec",  # noqa E501
        ]
    return fpaths


@pytest.mark.parametrize("fpath_descriptor", get_fpaths_descriptors())
def test_boutiques_descriptors(fpath_descriptor):
    bosh(["validate", fpath_descriptor])


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("bids-validator", "2.0.3", None),
        ("fmriprep", "20.2.7", None),
        ("fmriprep", "23.1.3", None),
        ("fmriprep", "24.1.1", None),
        ("mriqc", "23.1.0", None),
        ("qsiprep", "0.23.0", None),
        ("rabies", "0.5.1", "preprocess"),
        ("rabies", "0.5.1", "confound-correction"),
        ("rabies", "0.5.1", "analysis"),
    ],
)
def test_pipeline_runner(
    pipeline_name,
    pipeline_version,
    pipeline_step,
    single_subject_dataset,
):
    layout, participant_id, session_id = single_subject_dataset
    layout: DatasetLayout
    runner = PipelineRunner(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
        simulate=True,
    )
    runner.layout = layout
    runner.pipeline_config.get_fpath_container().touch()
    invocation_str, descriptor_str = runner.run_single(
        participant_id=participant_id, session_id=session_id
    )

    assert TEMPLATE_REPLACE_PATTERN.search(invocation_str) is None
    assert TEMPLATE_REPLACE_PATTERN.search(descriptor_str) is None


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("heudiconv", "0.12.2", "prepare"),
        ("heudiconv", "0.12.2", "convert"),
        ("dcm2bids", "3.1.0", "prepare"),
        ("dcm2bids", "3.1.0", "convert"),
        ("dcm2bids", "3.2.0", "prepare"),
        ("dcm2bids", "3.2.0", "convert"),
        ("bidscoin", "4.3.2", "prepare"),
        ("bidscoin", "4.3.2", "edit"),
        ("bidscoin", "4.3.2", "convert"),
    ],
)
def test_bids_conversion_runner(
    pipeline_name, pipeline_version, pipeline_step, single_subject_dataset
):
    layout, participant_id, session_id = single_subject_dataset
    layout: DatasetLayout
    runner = BidsConversionRunner(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
        simulate=True,
    )

    fpath_container = runner.pipeline_config.get_fpath_container()
    if fpath_container is not None:
        runner.pipeline_config.get_fpath_container().touch()

    invocation_str, descriptor_str = runner.run_single(
        participant_id=participant_id, session_id=session_id
    )

    assert TEMPLATE_REPLACE_PATTERN.search(invocation_str) is None
    assert TEMPLATE_REPLACE_PATTERN.search(descriptor_str) is None


def test_bids_pipeline_configs(bids_pipeline_configs: list[BidsPipelineConfig]):
    for pipeline_config in bids_pipeline_configs:
        count = sum([step.UPDATE_STATUS for step in pipeline_config.STEPS])
        assert count == 1, (
            f"BIDS pipeline {pipeline_config.NAME} {pipeline_config.VERSION}"
            f" should have exactly one step with UPDATE_STATUS=true (got {count})"
        )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("fmriprep", "20.2.7", DEFAULT_PIPELINE_STEP_NAME),
        ("fmriprep", "23.1.3", DEFAULT_PIPELINE_STEP_NAME),
        ("fmriprep", "24.1.1", DEFAULT_PIPELINE_STEP_NAME),
        ("freesurfer", "6.0.1", DEFAULT_PIPELINE_STEP_NAME),
        ("freesurfer", "7.3.2", DEFAULT_PIPELINE_STEP_NAME),
        ("mriqc", "23.1.0", DEFAULT_PIPELINE_STEP_NAME),
        ("qsiprep", "0.23.0", DEFAULT_PIPELINE_STEP_NAME),
    ],
)
def test_tracker(
    pipeline_name, pipeline_version, pipeline_step, single_subject_dataset
):
    layout, participant_id, session_id = single_subject_dataset
    layout: DatasetLayout
    tracker = PipelineTracker(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
    )

    # make sure all template strings are replaced
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tracker.run_single(participant_id=participant_id, session_id=session_id)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step,fn_fpaths_generator",
    [
        ("fmriprep", "20.2.7", DEFAULT_PIPELINE_STEP_NAME, get_fmriprep_output_paths),
        ("fmriprep", "23.1.3", DEFAULT_PIPELINE_STEP_NAME, get_fmriprep_output_paths),
        ("fmriprep", "24.1.1", DEFAULT_PIPELINE_STEP_NAME, get_fmriprep_output_paths),
        ("mriqc", "23.1.0", DEFAULT_PIPELINE_STEP_NAME, get_mriqc_output_paths),
        ("qsiprep", "0.23.0", DEFAULT_PIPELINE_STEP_NAME, get_qsiprep_output_paths),
    ],
)
def test_tracker_paths(
    pipeline_name,
    pipeline_version,
    pipeline_step,
    fn_fpaths_generator,
    single_subject_dataset,
):
    layout, participant_id, session_id = single_subject_dataset
    layout: DatasetLayout
    tracker = PipelineTracker(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
    )

    # create files
    for fpath_relative in fn_fpaths_generator(
        participant_id, session_id, pipeline_version
    ):
        fpath: Path = tracker.dpath_pipeline_output / fpath_relative
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    # run tracker
    tracker.run_single(participant_id=participant_id, session_id=session_id)

    # check status
    assert (
        tracker.processing_status_table.loc[
            (
                (
                    tracker.processing_status_table[
                        tracker.processing_status_table.col_participant_id
                    ]
                    == participant_id
                )
                & (
                    tracker.processing_status_table[
                        tracker.processing_status_table.col_session_id
                    ]
                    == session_id
                )
            ),
            tracker.processing_status_table.col_status,
        ].item()
        == tracker.processing_status_table.status_success
    )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version",
    [
        ("fs_stats", "0.2.1"),
        ("static_FC", "0.1.0"),
    ],
)
def test_extractor(
    pipeline_name,
    pipeline_version,
    single_subject_dataset,
):
    layout, participant_id, session_id = single_subject_dataset
    layout: DatasetLayout
    runner = ExtractionRunner(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        simulate=True,
    )

    if (fpath_container := runner.pipeline_config.get_fpath_container()) is not None:
        fpath_container.touch()

    invocation_str, descriptor_str = runner.run_single(
        participant_id=participant_id, session_id=session_id
    )

    assert TEMPLATE_REPLACE_PATTERN.search(invocation_str) is None
    assert TEMPLATE_REPLACE_PATTERN.search(descriptor_str) is None


@pytest.mark.parametrize(
    "pipeline_type,pipeline_name,pipeline_version",
    [
        (PipelineTypeEnum.BIDSIFICATION, "bidscoin", "4.3.2"),
        (PipelineTypeEnum.BIDSIFICATION, "dcm2bids", "3.1.0"),
        (PipelineTypeEnum.BIDSIFICATION, "dcm2bids", "3.2.0"),
        (PipelineTypeEnum.BIDSIFICATION, "heudiconv", "0.12.2"),
        (PipelineTypeEnum.PROCESSING, "fmriprep", "20.2.7"),
        (PipelineTypeEnum.PROCESSING, "fmriprep", "23.1.3"),
        (PipelineTypeEnum.PROCESSING, "fmriprep", "24.1.1"),
        (PipelineTypeEnum.PROCESSING, "freesurfer", "6.0.1"),
        (PipelineTypeEnum.PROCESSING, "freesurfer", "7.3.2"),
        (PipelineTypeEnum.PROCESSING, "mriqc", "23.1.0"),
        (PipelineTypeEnum.PROCESSING, "qsiprep", "0.23.0"),
        (PipelineTypeEnum.EXTRACTION, "fs_stats", "0.2.1"),
        (PipelineTypeEnum.EXTRACTION, "static_FC", "0.1.0"),
    ],
)
def test_pipeline_variables(pipeline_type, pipeline_name, pipeline_version):
    main_config = Config.load(FPATH_SAMPLE_CONFIG)
    variables_in_main_config = set(
        main_config.PIPELINE_VARIABLES.get_variables(
            pipeline_type, pipeline_name, pipeline_version
        ).keys()
    )
    pipeline_config = BasePipelineConfig(
        **load_json(
            DPATH_SAMPLE_PIPELINES
            / pipeline_type.value
            / f"{pipeline_name}-{pipeline_version}"
            / DatasetLayout.fname_pipeline_config
        )
    )
    variables_in_pipeline_config = set(pipeline_config.VARIABLES.keys())
    assert variables_in_main_config == variables_in_pipeline_config
