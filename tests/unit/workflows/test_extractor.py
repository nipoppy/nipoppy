"""Tests for ExtractionWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.pipeline import ExtractionPipelineConfig, PipelineInfo
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME
from nipoppy.tabular.processing_status import ProcessingStatusTable
from nipoppy.utils import (
    participant_id_to_bids_participant_id,
    session_id_to_bids_session_id,
)
from nipoppy.workflows.extractor import ExtractionRunner
from tests.conftest import (
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
)


@pytest.fixture(scope="function")
def extractor(tmp_path: Path) -> ExtractionRunner:
    extractor = ExtractionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="fs_extractor",
        pipeline_version="2.0.0",
        pipeline_step=DEFAULT_PIPELINE_STEP_NAME,
    )
    extractor.config = get_config()
    create_empty_dataset(extractor.dpath_root)
    create_pipeline_config_files(
        extractor.layout.dpath_pipelines,
        processing_pipelines=[
            {
                "NAME": "freesurfer",
                "VERSION": "7.3.2",
                "STEPS": [
                    # field unique to ProcPipelineStepConfig
                    {"TRACKER_CONFIG_FILE": "tracker_config.json"}
                ],
            },
        ],
        extraction_pipelines=[
            {
                "NAME": "fs_extractor",
                "VERSION": "2.0.0",
                "PROC_DEPENDENCIES": [
                    {
                        "NAME": "freesurfer",
                        "VERSION": "7.3.2",
                    },
                ],
                "STEPS": [{}],
            },
            {
                "NAME": "fs_fmriprep_extractor",
                "VERSION": "1.0.0",
                "PROC_DEPENDENCIES": [
                    {
                        "NAME": "freesurfer",
                        "VERSION": "6.0.1",
                    },
                    {
                        "NAME": "fmriprep",
                        "VERSION": "20.0.7",
                    },
                ],
                "STEPS": [{}],
            },
        ],
    )
    return extractor


@pytest.mark.parametrize(
    "attribute,expected",
    [
        ("dpath_pipeline", "derivatives/freesurfer/7.3.2"),
        ("dpath_pipeline_output", "derivatives/freesurfer/7.3.2/output"),
        ("dpath_pipeline_idp", "derivatives/freesurfer/7.3.2/idp"),
    ],
)
def test_paths(extractor: ExtractionRunner, attribute, expected):
    assert getattr(extractor, attribute) == extractor.dpath_root / expected


def test_setup(extractor: ExtractionRunner):
    assert not extractor.dpath_pipeline_idp.exists()
    extractor.run_setup()
    assert extractor.dpath_pipeline_idp.exists()


def test_dpath_pipeline(extractor: ExtractionRunner):
    assert (
        extractor.dpath_pipeline
        == extractor.layout.dpath_derivatives / "freesurfer" / "7.3.2"
    )


def test_proc_pipeline_info(extractor: ExtractionRunner):
    # check that proc_pipeline_info calls _get_pipeline_config with the
    # correct pipeline_class
    assert isinstance(extractor.proc_pipeline_info, PipelineInfo)


def test_proc_pipeline_info_error(extractor: ExtractionRunner):
    bad_version = "invalid_version"
    extractor.pipeline_config.PROC_DEPENDENCIES[0].VERSION = bad_version
    with pytest.raises(
        FileNotFoundError, match=f"Pipeline config file not found at .* {bad_version}"
    ):
        extractor.proc_pipeline_info


@pytest.mark.parametrize(
    "processing_status_data,pipeline_name,pipeline_version,participant_id,session_id,expected",  # noqa: E501
    [
        (
            [
                [
                    "S01",
                    "1",
                    "freesurfer",
                    "7.3.2",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "S01",
                    "2",
                    "freesurfer",
                    "7.3.2",
                    ProcessingStatusTable.status_incomplete,
                ],
                ["S01", "3", "freesurfer", "7.3.2", ProcessingStatusTable.status_fail],
                [
                    "S02",
                    "1",
                    "freesurfer",
                    "7.3.2",
                    ProcessingStatusTable.status_unavailable,
                ],
                [
                    "S02",
                    "2",
                    "freesurfer",
                    "7.3.2",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "fs_extractor",
            "2.0.0",
            None,
            None,
            [("S01", "1"), ("S02", "2")],
        ),
        (
            [
                [
                    "S01",
                    "1",
                    "freesurfer",
                    "7.3.2",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "fs_extractor",
            "2.0.0",
            "S02",  # S02 is not in processing status table
            "1",
            [],
        ),
        (
            [
                [
                    "P01",
                    "A",
                    "freesurfer",
                    "6.0.1",
                    ProcessingStatusTable.status_success,
                ],
                ["P01", "B", "freesurfer", "6.0.1", ProcessingStatusTable.status_fail],
                [
                    "P02",
                    "B",
                    "freesurfer",
                    "6.0.1",
                    ProcessingStatusTable.status_success,
                ],
                ["P01", "A", "fmriprep", "20.0.7", ProcessingStatusTable.status_fail],
                [
                    "P01",
                    "B",
                    "fmriprep",
                    "20.0.7",
                    ProcessingStatusTable.status_success,
                ],
                [
                    "P02",
                    "B",
                    "fmriprep",
                    "20.0.7",
                    ProcessingStatusTable.status_success,
                ],
            ],
            "fs_fmriprep_extractor",
            "1.0.0",
            "P02",
            "B",
            [("P02", "B")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    processing_status_data,
    pipeline_name,
    pipeline_version,
    participant_id,
    session_id,
    expected,
    extractor: ExtractionRunner,
):
    extractor.pipeline_name = pipeline_name
    extractor.pipeline_version = pipeline_version
    extractor.pipeline_step = DEFAULT_PIPELINE_STEP_NAME
    extractor.processing_status_table = ProcessingStatusTable().add_or_update_records(
        records=[
            {
                ProcessingStatusTable.col_participant_id: data[0],
                ProcessingStatusTable.col_session_id: data[1],
                ProcessingStatusTable.col_bids_participant_id: participant_id_to_bids_participant_id(
                    data[0]
                ),
                ProcessingStatusTable.col_bids_session_id: session_id_to_bids_session_id(
                    data[1]
                ),
                ProcessingStatusTable.col_pipeline_name: data[2],
                ProcessingStatusTable.col_pipeline_version: data[3],
                ProcessingStatusTable.col_pipeline_step: DEFAULT_PIPELINE_STEP_NAME,
                ProcessingStatusTable.col_status: data[4],
            }
            for data in processing_status_data
        ]
    )
    assert [
        tuple(x)
        for x in extractor.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


def test_run_single(
    extractor: ExtractionRunner,
    mocker: pytest_mock.MockerFixture,
):
    mocked_process_container_config = mocker.patch(
        "nipoppy.workflows.runner.PipelineRunner.process_container_config",
        # usually returns string and config object
        return_value=(None, mocker.MagicMock()),
    )
    mocked_launch_boutiques_container = mocker.patch(
        "nipoppy.workflows.runner.PipelineRunner.launch_boutiques_run"
    )

    extractor.run_single("S01", "BL")
    assert mocked_process_container_config.call_count == 1
    mocked_process_container_config.assert_called_once_with(
        participant_id="S01",
        session_id="BL",
        bind_paths=[extractor.dpath_pipeline_idp, extractor.dpath_pipeline_output],
    )
    assert mocked_launch_boutiques_container.call_count == 1


def test_check_pipeline_version(extractor: ExtractionRunner):
    extractor.pipeline_name = "fs_extractor"
    extractor.pipeline_version = None

    extractor.check_pipeline_version()
    assert extractor.pipeline_version == "2.0.0"


def test_pipeline_config(extractor: ExtractionRunner):
    assert isinstance(extractor.pipeline_config, ExtractionPipelineConfig)


@pytest.mark.parametrize(
    "init_params,participant_id,session_id,expected_command",
    [
        (
            {"dpath_root": "/path/to/root", "pipeline_name": "my_pipeline"},
            "P01",
            "1",
            [
                "nipoppy",
                "extract",
                "--dataset",
                "/path/to/root",
                "--pipeline",
                "my_pipeline",
                "--participant-id",
                "P01",
                "--session-id",
                "1",
            ],
        ),
        (
            {
                "dpath_root": "/path/to/other/root",
                "pipeline_name": "other_pipeline",
                "pipeline_version": "1.0.0",
                "pipeline_step": "step1",
                "participant_id": "ShouldNotBeUsed",  # should be skipped
                "session_id": "ShouldNotBeUsed",  # should be skipped
                "simulate": True,  # should be skipped
                "keep_workdir": True,
                "hpc": "slurm",  # should be skipped
                "use_list": "/path/to/list",  # should be skipped
                "fpath_layout": "/path/to/layout",
                "dry_run": True,  # should be skipped
                "verbose": True,
            },
            "P01",
            "1",
            [
                "nipoppy",
                "extract",
                "--dataset",
                "/path/to/other/root",
                "--pipeline",
                "other_pipeline",
                "--pipeline-version",
                "1.0.0",
                "--pipeline-step",
                "step1",
                "--participant-id",
                "P01",
                "--session-id",
                "1",
                "--keep-workdir",
                "--layout",
                "/path/to/layout",
                "--verbose",
            ],
        ),
    ],
)
def test_generate_cli_command_for_hpc(
    init_params,
    participant_id,
    session_id,
    expected_command,
    mocker: pytest_mock.MockFixture,
):
    mocker.patch("nipoppy.workflows.base.DatasetLayout")
    runner = ExtractionRunner(**init_params)
    assert (
        runner._generate_cli_command_for_hpc(participant_id, session_id)
        == expected_command
    )
