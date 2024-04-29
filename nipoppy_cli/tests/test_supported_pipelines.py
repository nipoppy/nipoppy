"""Test that all supported pipelines can run successfully in simulate mode."""

from pathlib import Path

import pytest
import pytest_mock
from boutiques import bosh

from nipoppy.layout import DatasetLayout
from nipoppy.utils import DPATH_DESCRIPTORS, FPATH_SAMPLE_CONFIG
from nipoppy.workflows import BidsConversionRunner, PipelineRunner

from .conftest import create_empty_dataset, prepare_dataset


@pytest.fixture()
def single_subject_dataset(
    tmp_path: Path, mocker: pytest_mock.MockerFixture
) -> DatasetLayout:
    dataset_root = tmp_path / "my_dataset"
    participant = "01"
    session = "ses-01"
    container_command = "apptainer"
    config_files_map = {
        "<PATH_TO_FREESURFER_LICENSE_FILE>": "freesurfer_license.txt",
        "<PATH_TO_HEURISTIC_FILE>": "heuristic.py",
        "<PATH_TO_CONFIG_FILE>": "dcm2bids_config.json",
    }

    participants_and_sessions = {participant: [session]}

    layout = DatasetLayout(dataset_root)
    create_empty_dataset(dataset_root)
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=layout.dpath_bids,
    )
    manifest.save_with_backup(layout.fpath_manifest)

    config_text = FPATH_SAMPLE_CONFIG.read_text()
    for placeholder, fname in config_files_map.items():
        fpath = layout.dpath_root / fname
        config_text = config_text.replace(placeholder, str(fpath))
        fpath.touch()
    layout.fpath_config.write_text(config_text)

    # patch so that the test runs even if the command is not available
    mocker.patch(
        "nipoppy.config.container.check_container_command",
        return_value=container_command,
    )

    return layout, participant, session


def get_fpaths_descriptors() -> list[str]:
    return [str(fpath) for fpath in Path(DPATH_DESCRIPTORS).iterdir()]


@pytest.mark.parametrize("fpath_descriptor", get_fpaths_descriptors())
def test_boutiques_descriptors(fpath_descriptor):
    bosh(["validate", fpath_descriptor])


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version",
    [
        ("fmriprep", "20.2.7"),
        ("fmriprep", "23.1.3"),
        ("mriqc", "23.1.0"),
    ],
)
def test_pipeline_runner(pipeline_name, pipeline_version, single_subject_dataset):
    layout, participant, session = single_subject_dataset
    layout: DatasetLayout
    runner = PipelineRunner(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        simulate=True,
    )

    fpath_container: Path = layout.dpath_containers / runner.pipeline_config.CONTAINER
    fpath_container.touch()

    runner.run_single(participant=participant, session=session)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("heudiconv", "0.12.2", "prepare"),
        ("heudiconv", "0.12.2", "convert"),
        ("dcm2bids", "3.1.0", "prepare"),
        ("dcm2bids", "3.1.0", "convert"),
    ],
)
def test_bids_conversion_runner(
    pipeline_name, pipeline_version, pipeline_step, single_subject_dataset
):
    layout, participant, session = single_subject_dataset
    layout: DatasetLayout
    runner = BidsConversionRunner(
        dpath_root=layout.dpath_root,
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        pipeline_step=pipeline_step,
        simulate=True,
    )

    fpath_container: Path = layout.dpath_containers / runner.pipeline_config.CONTAINER
    fpath_container.touch()

    runner.run_single(participant=participant, session=session)
