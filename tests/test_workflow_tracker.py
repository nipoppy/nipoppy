"""Tests for the PipelineTracker class."""

import json
import logging
from pathlib import Path

import pandas as pd
import pytest

from nipoppy.config.main import Config
from nipoppy.env import DEFAULT_PIPELINE_STEP_NAME
from nipoppy.tabular.bagel import Bagel
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.runner import PipelineRunner
from nipoppy.workflows.tracker import PipelineTracker

from .conftest import create_empty_dataset, get_config, prepare_dataset


@pytest.fixture(scope="function")
def tracker(tmp_path: Path):
    participants_and_sessions = {
        "01": ["1", "2"],
        "02": ["1", "2"],
    }

    tracker = PipelineTracker(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="test_pipeline",
        pipeline_version="0.1.0",
        pipeline_step=DEFAULT_PIPELINE_STEP_NAME,
    )

    create_empty_dataset(tracker.dpath_root)

    manifest: Manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
    )
    manifest.save_with_backup(tracker.layout.fpath_manifest)

    fpath_tracker_config = tmp_path / "tracker_config.json"
    tracker_config = {
        "PATHS": [
            "[[NIPOPPY_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]/results.txt",
            "file.txt",
        ],
        "PARTICIPANT_SESSION_DIR": "[[NIPOPPY_PARTICIPANT_ID]]/[[NIPOPPY_BIDS_SESSION_ID]]",
    }

    fpath_tracker_config.write_text(json.dumps(tracker_config))

    config: Config = get_config(
        visit_ids=["1", "2"],
        proc_pipelines=[
            {
                "NAME": tracker.pipeline_name,
                "VERSION": tracker.pipeline_version,
                "STEPS": [
                    {
                        "NAME": tracker.pipeline_step,
                        "TRACKER_CONFIG_FILE": fpath_tracker_config,
                    }
                ],
            },
        ],
    )
    config.save(tracker.layout.fpath_config)

    return tracker


def test_run_setup(tracker: PipelineTracker):
    tracker.run_setup()
    assert tracker.bagel.empty


def test_run_setup_existing_bagel(tracker: PipelineTracker):
    bagel = Bagel(
        data={
            Bagel.col_participant_id: ["01"],
            Bagel.col_session_id: ["1"],
            Bagel.col_pipeline_name: ["some_pipeline"],
            Bagel.col_pipeline_version: ["some_version"],
            Bagel.col_pipeline_step: ["some_step"],
            Bagel.col_status: [Bagel.status_success],
        }
    ).validate()
    bagel.save_with_backup(tracker.layout.fpath_imaging_bagel)

    tracker.run_setup()

    assert tracker.bagel.equals(bagel)


def test_run_setup_existing_bad_bagel(
    tracker: PipelineTracker, caplog: pytest.LogCaptureFixture
):
    # bagel with wrong columns
    bad_bagel = pd.DataFrame([{"col1": "val1"}])
    bad_bagel.to_csv(tracker.layout.fpath_imaging_bagel, index=False)

    tracker.run_setup()

    assert any(
        [
            record.levelno == logging.WARNING
            and "Failed to load existing bagel at " in record.message
            for record in caplog.records
        ]
    )
    assert tracker.bagel.empty


@pytest.mark.parametrize(
    "relative_paths,expected_status",
    [
        (["dirA/01_ses-1.txt", "dirA/dirB/file.txt"], Bagel.status_success),
        (["**/*.txt"], Bagel.status_success),
        (["*file.txt"], Bagel.status_fail),
        (["dirA/01_ses-1.txt", "dirA/dirB/file.txt", "missing.txt"], Bagel.status_fail),
    ],
)
def test_check_status(tracker: PipelineTracker, relative_paths, expected_status):
    for relative_path_to_write in ["dirA/01_ses-1.txt", "dirA/dirB/file.txt"]:
        fpath = tracker.dpath_pipeline_output / relative_path_to_write
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    assert tracker.check_status(relative_paths) == expected_status


@pytest.mark.parametrize(
    "relative_paths,relative_dpath_to_tar,expected_status",
    [
        (["dirA/01_ses-1.txt", "dirA/dirB/file.txt"], "dirA", Bagel.status_success),
        (["dirA/*.txt", "dirA/dirB/file.txt"], "dirA", Bagel.status_success),
        (["**/*.txt"], "dirA", Bagel.status_success),
        # # FAILING, see note in check_status
        # (["*file.txt"], "dirA", Bagel.status_fail),
        (
            ["dirA/01_ses-1.txt", "dirA/dirB/file.txt", "missing.txt"],
            "dirA",
            Bagel.status_fail,
        ),
        (
            ["dirA/01_ses-1.txt", "dirA/dirB/file.txt"],
            "dirA/dirB",
            Bagel.status_success,
        ),
    ],
)
def test_check_status_with_tarball(
    tracker: PipelineTracker,
    relative_paths: list[str],
    relative_dpath_to_tar: str,
    expected_status,
):
    for relative_path_to_write in ["dirA/01_ses-1.txt", "dirA/dirB/file.txt"]:
        fpath = tracker.dpath_pipeline_output / relative_path_to_write
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    # use PipelineRunner to tar the directory
    dpath_to_tar = tracker.dpath_pipeline_output / relative_dpath_to_tar
    PipelineRunner(
        tracker.dpath_root, tracker.pipeline_name, tracker.pipeline_version
    ).tar_directory(dpath_to_tar)

    assert not dpath_to_tar.exists()
    assert (
        tracker.check_status(relative_paths, relative_dpath_to_tar) == expected_status
    )


@pytest.mark.parametrize(
    "doughnut_data,participant_id,session_id,expected",
    [
        (
            [
                ["S01", "1", False],
                ["S01", "2", True],
                ["S02", "3", False],
            ],
            None,
            None,
            [("S01", "2")],
        ),
        (
            [
                ["P01", "A", False],
                ["P01", "B", True],
                ["P02", "B", True],
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
    tracker = PipelineTracker(
        dpath_root=tmp_path,
        pipeline_name="",
        pipeline_version="",
    )
    tracker.doughnut = Doughnut().add_or_update_records(
        records=[
            {
                Doughnut.col_participant_id: data[0],
                Doughnut.col_session_id: data[1],
                Doughnut.col_visit_id: data[1],
                Doughnut.col_in_bids: data[2],
                Doughnut.col_datatype: None,
                Doughnut.col_participant_dicom_dir: "",
                Doughnut.col_in_pre_reorg: False,
                Doughnut.col_in_post_reorg: False,
            }
            for data in doughnut_data
        ]
    )

    assert [
        tuple(x)
        for x in tracker.get_participants_sessions_to_run(
            participant_id=participant_id, session_id=session_id
        )
    ] == expected


@pytest.mark.parametrize(
    "participant_id,session_id,expected_status",
    [("01", "1", Bagel.status_success), ("02", "2", Bagel.status_fail)],
)
def test_run_single(
    participant_id, session_id, expected_status, tracker: PipelineTracker
):
    for relative_path_to_write in [
        "01/ses-1/results.txt",
        "file.txt",
        "02/ses-1/results.txt",
    ]:
        fpath = tracker.dpath_pipeline_output / relative_path_to_write
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.touch()

    for relative_dpath_to_tar in ["01/ses-1", "02/ses-1"]:
        dpath_to_tar = tracker.dpath_pipeline_output / relative_dpath_to_tar
        PipelineRunner(
            tracker.dpath_root, tracker.pipeline_name, tracker.pipeline_version
        ).tar_directory(dpath_to_tar)

    assert not dpath_to_tar.exists()
    assert tracker.run_single(participant_id, session_id) == expected_status

    assert (
        tracker.bagel.set_index([Bagel.col_participant_id, Bagel.col_session_id])
        .loc[:, Bagel.col_status]
        .item()
    ) == expected_status


def test_run_single_no_config(tracker: PipelineTracker):
    tracker.pipeline_config.STEPS[0].TRACKER_CONFIG_FILE = None
    with pytest.raises(ValueError, match="No tracker config file specified for"):
        tracker.run_single("01", "1")


@pytest.mark.parametrize(
    "bagel",
    [
        Bagel(),
        Bagel(
            data={
                Bagel.col_participant_id: ["01"],
                Bagel.col_session_id: ["1"],
                Bagel.col_pipeline_name: ["some_pipeline"],
                Bagel.col_pipeline_version: ["some_version"],
                Bagel.col_pipeline_step: ["some_step"],
                Bagel.col_status: [Bagel.status_success],
            }
        ).validate(),
    ],
)
def test_run_cleanup(tracker: PipelineTracker, bagel: Bagel):
    tracker.bagel = bagel
    tracker.run_cleanup()

    assert tracker.layout.fpath_imaging_bagel.exists()
    assert Bagel.load(tracker.layout.fpath_imaging_bagel).equals(bagel)


def test_run_no_create_work_directory(tracker: PipelineTracker):
    tracker.run()
    assert not tracker.dpath_pipeline_work.exists()


def test_run_no_rm_work_directory(tracker: PipelineTracker):
    tracker.dpath_pipeline_work.mkdir(parents=True)
    tracker.run()
    assert tracker.dpath_pipeline_work.exists()
