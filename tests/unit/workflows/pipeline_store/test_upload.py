"""Test for the PipelineUploadWorkflow class."""

from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import (
    ExecutionError,
    ReturnCode,
    TerminatedByUserError,
    WorkflowError,
)
from nipoppy.layout import DatasetLayout
from nipoppy.pipeline_validation import _load_pipeline_config_file
from nipoppy.workflows.pipeline_store.upload import (
    PipelineUploadWorkflow,
    _get_file_md5,
    _is_same_pipeline,
)
from tests.conftest import TEST_PIPELINE

DATASET_PATH = "my_dataset"


@pytest.fixture(scope="function")
def workflow(mocker: pytest_mock.MockerFixture):
    workflow = PipelineUploadWorkflow(
        dpath_pipeline=TEST_PIPELINE,
        zenodo_api=mocker.MagicMock(),
    )
    return workflow


def test_run_main(workflow: PipelineUploadWorkflow, mocker: pytest_mock.MockerFixture):
    metadata = {"metadata": {}}
    get_pipeline_metadata = mocker.patch.object(
        workflow, "_get_pipeline_metadata", return_value=metadata
    )
    validator = mocker.patch(
        "nipoppy.workflows.pipeline_store.upload.check_pipeline_bundle",
    )

    workflow.assume_yes = True
    workflow.force = True
    workflow.run_main()

    workflow.zenodo_api.upload_record.assert_called_once_with(
        input_dir=TEST_PIPELINE,
        record_id=None,
        metadata=metadata,
        default_preview_filename=DatasetLayout.fname_pipeline_config,
    )
    get_pipeline_metadata.assert_called_once()
    validator.assert_called_once_with(TEST_PIPELINE, strict=True)


def test_get_pipeline_metadata(workflow: PipelineUploadWorkflow, datetime_fixture):  # noqa F811
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
            "subjects": [
                {"subject": "Nipoppy"},
                {"subject": "pipeline_type:processing"},
                {"subject": "pipeline_name:fmriprep"},
                {"subject": "pipeline_version:24.1.1"},
                {"subject": "schema_version:1.0"},
            ],
        }
    }

    pipeline_config = _load_pipeline_config_file(TEST_PIPELINE / "config.json")

    results = workflow._get_pipeline_metadata(
        zenodo_metadata_file=TEST_PIPELINE / "zenodo.json",
        pipeline_config=pipeline_config,
    )

    assert results == expected


@pytest.mark.parametrize(
    "pipeline_config, zenodo_metadata, expected",
    [
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="fmriprep",
                VERSION="24.1.1",
                SCHEMA_VERSION="1.0",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1.0",
                ]
            },
            True,
        ),
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="mriqc",
                VERSION="23.1.0",
                SCHEMA_VERSION="1.0",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1.0",
                ]
            },
            False,
        ),
        (
            BasePipelineConfig(
                PIPELINE_TYPE=PipelineTypeEnum.PROCESSING,
                NAME="FMRIPREP",
                VERSION="24.1.1",
                SCHEMA_VERSION="1.0",
            ),
            {
                "keywords": [
                    "Nipoppy",
                    "pipeline_type:processing",
                    "pipeline_name:fmriprep",
                    "pipeline_version:24.1.1",
                    "schema_version:1.0",
                ]
            },
            True,
        ),
    ],
)
def test_is_same_pipeline(pipeline_config, zenodo_metadata, expected):
    assert _is_same_pipeline(pipeline_config, zenodo_metadata) == expected


def test_is_same_record(tmp_path: Path, workflow: PipelineUploadWorkflow):
    record_id = "123456"
    files = [tmp_path / "config.json", tmp_path / "zenodo.json"]
    for file_to_upload in files:
        file_to_upload.write_text(file_to_upload.name)
    workflow.zenodo_api._get_files_checksum.return_value = {
        record_file.name: _get_file_md5(record_file).removeprefix("md5:")
        for record_file in files
    }

    assert workflow._is_same_record(
        record_id=record_id,
        input_dir=tmp_path,
    )
    workflow.zenodo_api._get_files_checksum.assert_called_once_with(record_id)


def test_is_not_same_when_record_is_null(
    tmp_path: Path, workflow: PipelineUploadWorkflow
):
    assert not workflow._is_same_record(
        record_id=None,
        input_dir=tmp_path,
    )


def test_is_not_same_record_when_content_differs(
    tmp_path: Path, workflow: PipelineUploadWorkflow
):
    file_to_upload = tmp_path / "config.json"
    file_to_upload.write_text("pipeline config")
    workflow.zenodo_api._get_files_checksum.return_value = {
        file_to_upload.name: "md5:wrong"
    }

    assert not workflow._is_same_record(
        record_id="123456",
        input_dir=tmp_path,
    )


@pytest.mark.parametrize(
    "remote_filenames",
    [[], ["config.json", "extra.json"], ["renamed.json"]],
)
def test_is_not_same_record_when_filename_set_differs(
    remote_filenames: list[str],
    tmp_path: Path,
    workflow: PipelineUploadWorkflow,
):
    file_to_upload = tmp_path / "config.json"
    file_to_upload.write_text("pipeline config")
    workflow.zenodo_api._get_files_checksum.return_value = {
        filename: _get_file_md5(file_to_upload) for filename in remote_filenames
    }

    assert not workflow._is_same_record(
        record_id="123456",
        input_dir=tmp_path,
    )


@pytest.mark.parametrize("force", [True, False])
def test_upload_same_pipeline(
    workflow: PipelineUploadWorkflow,
    force: bool,
):
    workflow.record_id = "1234567"
    workflow.assume_yes = True
    workflow.force = force

    # Mock current pipeline metadata on Zenodo
    workflow.zenodo_api.get_record_metadata.return_value = {
        "keywords": [
            "Nipoppy",
            "pipeline_type:processing",
            "pipeline_name:mriqc",
            "pipeline_version:23.1.0",
            "schema_version:1.0",
        ]
    }

    # Fails if force is False
    with (
        nullcontext()
        if force
        else pytest.raises(
            WorkflowError,
            match="The pipeline metadata does not match the existing record",
        )
    ):
        workflow.run()


@pytest.mark.no_xdist
def test_unchanged_pipeline_skips_upload(
    workflow: PipelineUploadWorkflow,
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockerFixture,
):
    latest_record_id = "7654321"
    workflow.record_id = "1234567"
    workflow.zenodo_api.get_latest_version_id.return_value = latest_record_id
    workflow.zenodo_api.get_record_metadata.return_value = {
        "keywords": [
            "Nipoppy",
            "pipeline_type:processing",
            "pipeline_name:fmriprep",
            "pipeline_version:24.1.1",
            "schema_version:1",
        ]
    }
    is_same_record = mocker.patch.object(
        workflow,
        "_is_same_record",
        return_value=True,
    )
    _request_community_inclusion = mocker.patch.object(
        workflow, "_request_community_inclusion"
    )

    workflow.run_main()

    workflow.zenodo_api.upload_record.assert_not_called()
    is_same_record.assert_called_once_with(
        record_id=latest_record_id,
        input_dir=TEST_PIPELINE,
    )
    assert "files are unchanged; skipping upload" in caplog.text
    _request_community_inclusion.assert_called_once()


def test_upload_to_nipoppy_community(
    workflow: PipelineUploadWorkflow,
    mocker: pytest_mock.MockerFixture,
):
    metadata = {"metadata": {}}
    community_id = "nipoppy-community-id"
    mocker.patch.object(workflow, "_get_pipeline_metadata", return_value=metadata)
    mocker.patch.object(workflow, "_confirm_upload", return_value=True)
    mocker.patch(
        "nipoppy.workflows.pipeline_store.upload.check_pipeline_bundle",
    )
    workflow.community = True
    workflow.zenodo_api._get_community_id.return_value = community_id

    workflow.run_main()

    workflow.zenodo_api._get_community_id.assert_called_once_with("nipoppy")
    workflow.zenodo_api.upload_record.assert_called_once_with(
        input_dir=TEST_PIPELINE,
        record_id=None,
        metadata=metadata,
        default_preview_filename=DatasetLayout.fname_pipeline_config,
    )


def test_force_bypasses_unchanged_check(
    workflow: PipelineUploadWorkflow, mocker: pytest_mock.MockerFixture
):
    workflow.record_id = "1234567"
    workflow.assume_yes = True
    workflow.force = True
    workflow.zenodo_api.get_latest_version_id.return_value = "7654321"
    workflow.zenodo_api.get_record_metadata.return_value = {"keywords": []}
    is_same_record = mocker.patch.object(workflow, "_is_same_record")

    workflow.run_main()

    is_same_record.assert_not_called()
    workflow.zenodo_api.upload_record.assert_called_once()


class TestConfirmUpload:
    @pytest.mark.no_xdist
    def test_assume_yes(
        self,
        workflow: PipelineUploadWorkflow,
        caplog: pytest.LogCaptureFixture,
    ):
        """Test that the --assume-yes flag bypasses the confirmation prompt."""
        workflow.assume_yes = True

        with caplog.at_level("DEBUG"):
            workflow._confirm_upload()

        assert "Assuming yes to all prompts (--assume-yes flag)." in caplog.text

    @pytest.mark.parametrize(
        "is_interactive, is_terminal",
        [(True, False), (False, True)],
    )
    def test_no_tty(
        self,
        is_interactive: bool,
        is_terminal: bool,
        workflow: PipelineUploadWorkflow,
        mocker: pytest_mock.MockerFixture,
    ):
        """Test that a non-interactive terminal raises an ExecutionError."""
        console = mocker.patch(
            "nipoppy.workflows.pipeline_store.upload.CONSOLE_STDOUT",
        )
        console.is_interactive = is_interactive
        console.is_terminal = is_terminal

        with pytest.raises(ExecutionError, match="Non-interactive terminal detected."):
            workflow._confirm_upload()

    @pytest.mark.no_xdist
    def test_confirm(
        self,
        workflow: PipelineUploadWorkflow,
        caplog: pytest.LogCaptureFixture,
        mocker: pytest_mock.MockerFixture,
    ):
        """Test that accepting the confirmation prompt allows the upload to proceed."""
        console = mocker.patch(
            "nipoppy.workflows.pipeline_store.upload.CONSOLE_STDOUT",
        )
        console.confirm.return_value = True
        console.is_interactive = True
        console.is_terminal = True

        workflow._confirm_upload()
        assert "" == caplog.text  # No log or error raised

    def test_decline(
        self,
        workflow: PipelineUploadWorkflow,
        mocker: pytest_mock.MockerFixture,
    ):
        """Test that declining the confirmation prompt raises TerminatedByUserError."""
        console = mocker.patch(
            "nipoppy.workflows.pipeline_store.upload.CONSOLE_STDOUT",
        )
        console.confirm.return_value = False
        console.is_interactive = True
        console.is_terminal = True

        with pytest.raises(
            TerminatedByUserError, match="Zenodo upload cancelled by user."
        ):
            workflow._confirm_upload()


@pytest.mark.parametrize(
    "hits, potential_duplicates",
    [
        [
            [
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
                {"links": {"self_html": "https://zenodo.org/records/123456"}},
            ],
            [
                "https://zenodo.org/records/123456",
                "https://zenodo.org/records/123456",
                "https://zenodo.org/records/123456",
            ],
        ]
    ],
)
@pytest.mark.no_xdist
def test_upload_duplicate_record(
    workflow: PipelineUploadWorkflow,
    hits: list,
    potential_duplicates: list[str],
    caplog: pytest.LogCaptureFixture,
):
    workflow.assume_yes = True
    workflow.zenodo_api.search_records.return_value = {"hits": hits}

    with pytest.raises(
        WorkflowError,
        match="It looks like this pipeline already exists in Zenodo. Aborting.",
    ):
        workflow.run()
        assert ", ".join(potential_duplicates) in caplog.text


def test_force_upload_duplicate_record(workflow: PipelineUploadWorkflow):
    workflow.assume_yes = True
    workflow.force = True

    workflow.zenodo_api.search_records.return_value = {"hits": {"doi": "abc.123"}}

    workflow.run()


@pytest.mark.no_xdist
def test_fails_check_pipeline_bundle(
    workflow: PipelineUploadWorkflow,
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockerFixture,
):
    mocker.patch(
        "nipoppy.workflows.pipeline_store.upload.check_pipeline_bundle",
        side_effect=Exception("Mocked validation failed"),
    )

    workflow.assume_yes = True

    with pytest.raises(WorkflowError) as exc_info:
        workflow.run_main()

    assert exc_info.value.code == ReturnCode.WORKFLOW_FAILURE

    assert "Pipeline validation failed. Please check the pipeline files" in caplog.text
