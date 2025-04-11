from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.pipeline_store.validation import _load_pipeline_config_file
from nipoppy.workflows.zenodo import ZenodoDownloadWorkflow, ZenodoUploadWorkflow
from nipoppy.zenodo_api import ZenodoAPI

from .conftest import DPATH_TEST_DATA, TEST_PIPELINE, create_empty_dataset

DATASET_PATH = "my_dataset"


@pytest.fixture(scope="function")
def record_id():
    """Fixture for Zenodo ID.

    The Sandbox can be reset at any time, so the Zenodo ID may change.
    If the test fails verify the Zenodo record at:
    https://sandbox.zenodo.org/records/194256

    The test file is located at: tests/data/sample_pipelines/proc/fmriprep-24.1.1
    """
    return "194256"


def test_download(tmp_path: Path, record_id: str):
    dpath_root = tmp_path / DATASET_PATH
    dpath_pipelines = dpath_root / "pipelines"
    create_empty_dataset(dpath_root)

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoDownloadWorkflow(
        dpath_root=dpath_root,
        record_id=record_id,
        zenodo_api=zenodo_api,
    )
    workflow.run_main()

    # Check that the pipeline was downloaded and moved correctly
    assert not (dpath_pipelines / record_id).exists()
    assert (dpath_pipelines / TEST_PIPELINE.name).exists()


@pytest.mark.parametrize(
    "force, fails",
    [
        (True, False),
        (False, True),
    ],
)
def test_download_dir_exist(tmp_path: Path, record_id: str, force: bool, fails: bool):
    """Test the behavior when the download directory already exists."""
    dpath_root = tmp_path / DATASET_PATH
    dpath_pipelines = dpath_root / "pipelines"
    create_empty_dataset(dpath_root)

    download_dir = dpath_pipelines / record_id
    download_dir.mkdir(parents=True, exist_ok=True)
    assert download_dir.exists()

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoDownloadWorkflow(
        dpath_root=dpath_root,
        record_id=record_id,
        zenodo_api=zenodo_api,
        force=force,
    )
    with pytest.raises(SystemExit) if fails else nullcontext():
        workflow.run_main()


@pytest.mark.parametrize(
    "force, fails",
    [
        (True, False),
        (False, True),
    ],
)
def test_download_install_dir_exist(
    tmp_path: Path,
    record_id: str,
    force: bool,
    fails: bool,
):
    dpath_root = tmp_path / DATASET_PATH
    dpath_pipelines = dpath_root / "pipelines"
    create_empty_dataset(dpath_root)

    download_dir = dpath_pipelines / TEST_PIPELINE.name
    download_dir.mkdir(parents=True, exist_ok=True)
    assert download_dir.exists()

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoDownloadWorkflow(
        dpath_root=dpath_root,
        record_id=record_id,
        zenodo_api=zenodo_api,
        force=force,
    )
    with pytest.raises(SystemExit) if fails else nullcontext():
        workflow.run_main()


def test_upload(mocker: pytest_mock.MockerFixture):
    upload_pipeline = mocker.patch(
        "nipoppy.zenodo_api.ZenodoAPI.upload_pipeline",
    )
    get_pipeline_metadata = mocker.patch(
        "nipoppy.workflows.zenodo.ZenodoUploadWorkflow._get_pipeline_metadata",
    )
    validator = mocker.patch(
        "nipoppy.workflows.zenodo.check_pipeline_bundle",
    )

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,
        zenodo_api=zenodo_api,
    )
    workflow.run_main()

    upload_pipeline.assert_called_once()
    get_pipeline_metadata.assert_called_once()
    validator.assert_called_once()


def test_get_pipeline_metadata(
    tmp_path: Path,
    datetime_fixture,
):  # noqa F811
    expected = {
        "metadata": {
            "title": "Upload test",
            "description": "This is a test upload",
            "creators": [
                {
                    "person_or_org": {
                        "given_name": "Nipoppy",
                        "family_name": "Test",
                        "type": "personal",
                    }
                }
            ],
            "publication_date": "2024-04-04",
            "publisher": "Nipoppy",
            "resource_type": {"id": "software"},
            "keywords": ["Nipoppy", "processing"],
        }
    }

    zenodo_api = ZenodoAPI(sandbox=True)
    workflow = ZenodoUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,
        zenodo_api=zenodo_api,
    )

    pipeline_config = _load_pipeline_config_file(TEST_PIPELINE / "config.json")

    results = workflow._get_pipeline_metadata(
        zenodo_metadata_file=TEST_PIPELINE / "zenodo.json",
        pipeline_config=pipeline_config,
    )
    # Convert keywords to set to prevent order mismatch
    results["metadata"]["keywords"] = set(results["metadata"]["keywords"])
    expected["metadata"]["keywords"] = set(expected["metadata"]["keywords"])

    assert results == expected
