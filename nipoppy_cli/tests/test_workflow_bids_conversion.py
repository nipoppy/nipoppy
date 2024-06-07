"""Tests for BidsConversionWorkflow."""

from pathlib import Path

import pytest

from nipoppy.config.main import Config
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
                "STEPS": [{"NAME": "prepare"}, {"NAME": "convert"}],
            },
            {
                "NAME": "dcm2bids",
                "VERSION": "3.1.0",
                "STEPS": [{"NAME": "prepare"}, {"NAME": "convert"}],
            },
        ]
    )


def test_setup(config: Config, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="heudiconv",
        pipeline_version="0.12.2",
        pipeline_step="prepare",
    )
    create_empty_dataset(workflow.dpath_root)
    config.save(workflow.layout.fpath_config)
    workflow.run_setup()
    assert not workflow.dpath_pipeline.exists()


@pytest.mark.parametrize(
    "doughnut",
    [
        Doughnut(),
        Doughnut(
            data={
                Doughnut.col_participant_id: ["01"],
                Doughnut.col_visit: ["1"],
                Doughnut.col_session: ["ses-1"],
                Doughnut.col_datatype: "['anat']",
                Doughnut.col_bids_id: ["sub-01"],
                Doughnut.col_dicom_id: ["01"],
                Doughnut.col_participant_dicom_dir: ["01"],
                Doughnut.col_downloaded: [True],
                Doughnut.col_organized: [True],
                Doughnut.col_bidsified: [True],
            }
        ).validate(),
    ],
)
def test_cleanup(doughnut: Doughnut, tmp_path: Path):
    workflow = BidsConversionRunner(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="",
        pipeline_version="",
        pipeline_step="",
    )
    workflow.doughnut = doughnut

    workflow.run_cleanup()

    assert workflow.layout.fpath_doughnut.exists()
    assert Doughnut.load(workflow.layout.fpath_doughnut).equals(doughnut)
