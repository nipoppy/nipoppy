"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.pipeline import BIDSificationPipelineConfig
from nipoppy.tabular.curation_status import CurationStatusTable
from nipoppy.workflows.bids_conversion import BIDSificationRunner
from tests.conftest import (
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
)


@pytest.fixture
def workflow(tmp_path: Path) -> BIDSificationRunner:
    workflow = BIDSificationRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    workflow.study.config = get_config()
    create_empty_dataset(workflow.dpath_root)
    create_pipeline_config_files(
        workflow.study.layout.dpath_pipelines,
        bidsification_pipelines=[
            {
                "NAME": "heudiconv",
                "VERSION": "0.12.2",
                "STEPS": [
                    {"NAME": "prepare"},
                    {"NAME": "convert", "UPDATE_STATUS": True},
                ],
            },
            {
                "NAME": "dcm2bids",
                "VERSION": "3.1.0",
                "STEPS": [
                    {"NAME": "prepare"},
                    {"NAME": "convert", "UPDATE_STATUS": True},
                ],
            },
        ],
    )
    return workflow


@pytest.mark.parametrize(
    "pipeline_name,expected_version",
    [
        ("heudiconv", "0.12.2"),
        ("dcm2bids", "3.1.0"),
    ],
)
def test_check_pipeline_version(
    pipeline_name,
    expected_version,
    workflow: BIDSificationRunner,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = None
    workflow.check_pipeline_version()
    assert workflow.pipeline_version == expected_version


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version",
    [
        ("heudiconv", "0.12.2"),
        ("dcm2bids", "3.1.0"),
    ],
)
def test_pipeline_config(
    pipeline_name, pipeline_version, workflow: BIDSificationRunner
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version
    assert isinstance(workflow.pipeline_config, BIDSificationPipelineConfig)


def test_dpath_pipeline_error(workflow: BIDSificationRunner):
    with pytest.raises(
        RuntimeError, match='"dpath_pipeline" attribute is not available for '
    ):
        workflow.dpath_pipeline


def test_setup(workflow: BIDSificationRunner):
    # check that the working directory is created
    assert not workflow.dpath_pipeline_work.exists()
    workflow.run_setup()
    assert workflow.dpath_pipeline_work.exists()


@pytest.mark.parametrize("update_status", [True, False])
def test_run_single(
    update_status, workflow: BIDSificationRunner, mocker: pytest_mock.MockerFixture
):
    workflow.curation_status_table = CurationStatusTable()
    workflow.pipeline_step_config.UPDATE_STATUS = update_status

    mocked_process_container_config = mocker.patch.object(
        workflow,
        "process_container_config",
        # usually returns string and config object
        return_value=(None, mocker.MagicMock()),
    )
    mocked_launch_boutiques_run = mocker.patch.object(workflow, "launch_boutiques_run")

    mocked_set_status = mocker.patch.object(
        workflow.curation_status_table, "set_status"
    )

    workflow.run_single("01", "1")

    mocked_process_container_config.assert_called_once()
    mocked_launch_boutiques_run.assert_called_once()

    if update_status:
        mocked_set_status.assert_called_once()
    else:
        mocked_set_status.assert_not_called()


@pytest.mark.parametrize(
    "table",
    [
        CurationStatusTable(),
        CurationStatusTable(
            data={
                CurationStatusTable.col_participant_id: ["01"],
                CurationStatusTable.col_visit_id: ["1"],
                CurationStatusTable.col_session_id: ["1"],
                CurationStatusTable.col_datatype: "['anat']",
                CurationStatusTable.col_participant_dicom_dir: ["01"],
                CurationStatusTable.col_in_pre_reorg: [True],
                CurationStatusTable.col_in_post_reorg: [True],
                CurationStatusTable.col_in_bids: [True],
            }
        ).validate(),
    ],
)
def test_cleanup(table: CurationStatusTable, workflow: BIDSificationRunner):
    workflow.pipeline_step = "convert"
    workflow.curation_status_table = table

    workflow.run_cleanup()

    assert workflow.study.layout.fpath_curation_status.exists()
    assert CurationStatusTable.load(workflow.study.layout.fpath_curation_status).equals(
        table
    )


def test_cleanup_simulate(workflow: BIDSificationRunner):
    workflow.pipeline_step = "convert"
    workflow.simulate = True
    workflow.curation_status_table = CurationStatusTable()

    workflow.run_cleanup()

    assert not workflow.study.layout.fpath_curation_status.exists()


def test_cleanup_no_status_update(workflow: BIDSificationRunner):
    workflow.pipeline_step = "prepare"
    workflow.curation_status_table = CurationStatusTable()

    workflow.run_cleanup()

    assert not workflow.study.layout.fpath_curation_status.exists()


@pytest.mark.parametrize(
    "status_data,participant_id,session_id,expected",
    [
        (
            [
                ["S01", "1", True, False],
                ["S01", "2", True, True],
                ["S02", "3", False, False],
            ],
            None,
            None,
            [("S01", "1")],
        ),
        (
            [
                ["P01", "A", True, False],
                ["P01", "B", True, False],
                ["P02", "B", True, False],
            ],
            "P01",
            "B",
            [("P01", "B")],
        ),
    ],
)
def test_get_participants_sessions_to_run(
    status_data, participant_id, session_id, expected, workflow: BIDSificationRunner
):
    workflow.curation_status_table = CurationStatusTable().add_or_update_records(
        records=[
            {
                CurationStatusTable.col_participant_id: data[0],
                CurationStatusTable.col_session_id: data[1],
                CurationStatusTable.col_in_post_reorg: data[2],
                CurationStatusTable.col_in_bids: data[3],
                CurationStatusTable.col_visit_id: data[1],
                CurationStatusTable.col_datatype: None,
                CurationStatusTable.col_participant_dicom_dir: "",
                CurationStatusTable.col_in_pre_reorg: False,
            }
            for data in status_data
        ]
    )
    assert [
        tuple(x)
        for x in workflow.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


def test_generate_cli_command_for_hpc(
    workflow: BIDSificationRunner,
    mocker: pytest_mock.MockFixture,
):
    mocked_generate_cli_command = mocker.patch.object(
        workflow.hpc_runner,
        "generate_cli_command",
    )
    workflow._generate_cli_command_for_hpc("p01", "s01")
    mocked_generate_cli_command.assert_called_once_with(
        participant_id="p01",
        session_id="s01",
    )
