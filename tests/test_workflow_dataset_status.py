"""Tests for the dataset status workflow."""

from pathlib import Path

import pytest

from nipoppy.tabular.bagel import Bagel
from nipoppy.tabular.doughnut import Doughnut
from nipoppy.tabular.manifest import Manifest
from nipoppy.workflows.dataset_status import StatusWorkflow

from .conftest import get_config


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


def test_run(dpath_root: Path):

    workflow = StatusWorkflow(dpath_root=dpath_root)

    workflow.config = get_config(dataset_name="my_dataset")

    manifest_dict = {
        Manifest.col_participant_id: ["01", "02", "03", "01", "02"],
        Manifest.col_session_id: ["BL", "BL", "BL", "M12", "M12"],
        Manifest.col_visit_id: ["BL", "BL", "BL", "M12", "M12"],
        Manifest.col_datatype: [
            ["anat", "dwi"],
            ["anat", "dwi"],
            ["anat", "dwi"],
            ["anat", "dwi"],
            ["anat", "dwi"],
        ],
    }

    doughnut_dict = {
        Doughnut.col_participant_id: ["01", "02", "03", "01"],
        Doughnut.col_session_id: ["BL", "BL", "BL", "M12"],
        Doughnut.col_visit_id: ["BL", "BL", "BL", "M12"],
        Doughnut.col_datatype: [
            ["anat", "dwi"],
            ["anat", "dwi"],
            ["anat", "dwi"],
            ["anat", "dwi"],
        ],
        Doughnut.col_participant_dicom_dir: [
            "/path/to/dicom",
            "/path/to/dicom",
            "/path/to/dicom",
            "/path/to/dicom",
        ],
        Doughnut.col_in_pre_reorg: [True, True, True, True],
        Doughnut.col_in_post_reorg: [True, True, True, False],
        Doughnut.col_in_bids: [True, True, False, False],
    }

    bagel_dict = {
        Bagel.col_participant_id: ["01", "02", "01", "02", "01"],
        Bagel.col_bids_participant_id: [
            "sub-01",
            "sub-02",
            "sub-01",
            "sub-02",
            "sub-01",
        ],
        Bagel.col_session_id: ["BL", "BL", "BL", "BL", "M12"],
        Bagel.col_bids_session_id: ["ses-BL", "ses-BL", "ses-BL", "ses-BL", "ses-M12"],
        Bagel.col_pipeline_name: [
            "dcm2bids",
            "dcm2bids",
            "fmriprep",
            "fmriprep",
            "dcm2bids",
        ],
        Bagel.col_pipeline_version: ["1.0.0", "1.0.0", "2.0.0", "2.0.0", "1.0.0"],
        Bagel.col_pipeline_step: [
            "convert",
            "convert",
            "default",
            "default",
            "convert",
        ],
        Bagel.col_status: ["SUCCESS", "SUCCESS", "SUCCESS", "INCOMPLETE", "FAIL"],
    }

    workflow.manifest = Manifest.from_dict(manifest_dict)
    workflow.doughnut = Doughnut.from_dict(doughnut_dict)
    workflow.bagel = Bagel.from_dict(bagel_dict)

    status_df = workflow.run_main()
    # status_df = status_df.fillna(0).astype(int).reset_index()

    print(status_df)
    # check manifest status
    assert set(status_df[Manifest.col_session_id].unique()) == set(["BL", "M12"])
    assert status_df[Manifest.col_session_id].nunique() == 2
    assert status_df["in_manifest"].sum() == 5

    # check doughnut status
    assert status_df["in_pre_reorg"].sum() == 4
    assert status_df["in_post_reorg"].sum() == 3
    assert status_df["in_bids"].sum() == 2

    # check bagel status
    assert status_df["dcm2bids\n1.0.0\nconvert"].sum() == 2
    assert status_df["fmriprep\n2.0.0\ndefault"].sum() == 1

    # check emoji status
    test_stickers = ["📋", "🍩", "🧹", "🥯", "🚀"]
    test_rewards = " ".join(test_stickers)
    calculated_rewards = status_df[status_df[Manifest.col_session_id] == "BL"][
        "rewards"
    ].values.astype(str)
    assert calculated_rewards == test_rewards
