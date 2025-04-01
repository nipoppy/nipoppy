"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.config.pipeline import BidsPipelineConfig
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.workflows.bids_conversion import BidsConversionRunner

from .conftest import create_empty_dataset, get_config


@pytest.fixture
def config() -> Config:
    return get_config(
        bids_pipelines=[
            {
                "NAME": "heudiconv",
                "VERSION": "0.12.2",
                "STEPS": [
                    {"NAME": "prepare"},
                    {"NAME": "convert", "UPDATE_DOUGHNUT": True},
                ],
            },
            {
                "NAME": "dcm2bids",
                "VERSION": "3.1.0",
                "STEPS": [
                    {"NAME": "prepare"},
                    {"NAME": "convert", "UPDATE_DOUGHNUT": True},
                ],
            },
        ]
    )


@pytest.mark.parametrize(
    "pipeline_name,expected_version",
    [
        ("heudiconv", "0.12.2"),
        ("dcm2bids", "3.1.0"),
    ],
)
def test_check_pipeline_version(
    pipeline_name, expected_version, config: Config, tmp_path: Path
):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path,
        pipeline_name=pipeline_name,
        pipeline_version=None,
    )
    config.save(workflow.layout.fpath_config)
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
    pipeline_name, pipeline_version, config: Config, tmp_path: Path
):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
    )
    config.save(workflow.layout.fpath_config)
    assert isinstance(workflow.pipeline_config, BidsPipelineConfig)


def test_dpath_pipeline_error(tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    with pytest.raises(
        RuntimeError, match='"dpath_pipeline" attribute is not available for '
    ):
        workflow.dpath_pipeline


def test_setup(config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    create_empty_dataset(workflow.dpath_root)
    config.save(workflow.layout.fpath_config)

    # check that the working directory is created
    assert not workflow.dpath_pipeline_work.exists()
    workflow.run_setup()
    assert workflow.dpath_pipeline_work.exists()


@pytest.mark.parametrize(
    "doughnut",
    [
        Doughnut(),
        Doughnut(
            data={
                Doughnut.col_participant_id: ["01"],
                Doughnut.col_visit_id: ["1"],
                Doughnut.col_session_id: ["1"],
                Doughnut.col_datatype: "['anat']",
                Doughnut.col_participant_dicom_dir: ["01"],
                Doughnut.col_in_pre_reorg: [True],
                Doughnut.col_in_post_reorg: [True],
                Doughnut.col_in_bids: [True],
            }
        ).validate(),
    ],
)
def test_cleanup(doughnut: Doughnut, config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="convert",
    )
    workflow.doughnut = doughnut
    config.save(workflow.layout.fpath_config)

    workflow.run_cleanup()

    assert workflow.layout.fpath_doughnut.exists()
    assert Doughnut.load(workflow.layout.fpath_doughnut).equals(doughnut)


def test_cleanup_simulate(tmp_path: Path, config: Config):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="convert",
        simulate=True,
    )
    workflow.doughnut = Doughnut()
    config.save(workflow.layout.fpath_config)

    workflow.run_cleanup()

    assert not workflow.layout.fpath_doughnut.exists()


def test_cleanup_no_doughnut_update(config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    workflow.doughnut = Doughnut()
    config.save(workflow.layout.fpath_config)

    workflow.run_cleanup()

    assert not workflow.layout.fpath_doughnut.exists()


@pytest.mark.parametrize(
    "doughnut_data,participant_id,session_id,expected",
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
    doughnut_data, participant_id, session_id, expected, tmp_path: Path
):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    workflow.doughnut = Doughnut().add_or_update_records(
        records=[
            {
                Doughnut.col_participant_id: data[0],
                Doughnut.col_session_id: data[1],
                Doughnut.col_in_post_reorg: data[2],
                Doughnut.col_in_bids: data[3],
                Doughnut.col_visit_id: data[1],
                Doughnut.col_datatype: None,
                Doughnut.col_participant_dicom_dir: "",
                Doughnut.col_in_pre_reorg: False,
            }
            for data in doughnut_data
        ]
    )
    assert [
        tuple(x)
        for x in workflow.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


@pytest.mark.parametrize(
    "init_params,participant_id,session_id,expected_command",
    [
        (
            {"dpath_root": "/path/to/root", "pipeline_name": "my_pipeline"},
            "P01",
            "1",
            [
                "nipoppy",
                "bidsify",
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
                "write_list": "/path/to/list",  # should be skipped
                "fpath_layout": "/path/to/layout",
                "dry_run": True,  # should be skipped
                "verbose": True,
            },
            "P01",
            "1",
            [
                "nipoppy",
                "bidsify",
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
    runner = BidsConversionRunner(**init_params)
    assert (
        runner._generate_cli_command_for_hpc(participant_id, session_id)
        == expected_command
    )
