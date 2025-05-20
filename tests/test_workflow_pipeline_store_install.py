"""Tests for PipelineInstallWorkflow class."""

import logging
import subprocess
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.config.pipeline import ProcPipelineConfig
from nipoppy.env import CURRENT_SCHEMA_VERSION, PipelineTypeEnum, ReturnCode
from nipoppy.layout import DatasetLayout
from nipoppy.workflows.pipeline_store.install import PipelineInstallWorkflow
from nipoppy.zenodo_api import ZenodoAPI

from .conftest import record_id  # noqa: F401
from .conftest import TEST_PIPELINE, create_pipeline_config_files, get_config


@pytest.fixture(scope="function")
def pipeline_config():
    return ProcPipelineConfig(
        **{
            "NAME": "my_pipeline",
            "VERSION": "1.0.0",
            "PIPELINE_TYPE": PipelineTypeEnum.PROCESSING,
            "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
            "CONTAINER_INFO": {
                "FILE": "[[NIPOPPY_DPATH_CONTAINERS]]/container.sif",
                "URI": "fake_uri",
            },
        }
    )


@pytest.fixture(scope="function")
def workflow(
    tmp_path: Path, pipeline_config: ProcPipelineConfig, mocker: pytest_mock.MockFixture
):
    dpath_root = tmp_path / "my_dataset"
    create_pipeline_config_files(
        tmp_path,
        processing_pipelines=[pipeline_config.model_dump(mode="json")],
    )
    workflow = PipelineInstallWorkflow(
        dpath_root=dpath_root,
        source=(
            tmp_path
            / DatasetLayout.pipeline_type_to_dname_map[PipelineTypeEnum.PROCESSING]
            / "my_pipeline-1.0.0"
        ),
        zenodo_api=ZenodoAPI(sandbox=True),
        assume_yes=True,
    )
    # make the default config have a path placeholder string
    get_config(dicom_dir_map_file="[[NIPOPPY_DPATH_ROOT]]/my_file.tsv").save(
        workflow.layout.fpath_config
    )

    # mock singularity/apptainer pull (this is overridden by some tests)
    mocker.patch.object(workflow, "run_command")

    return workflow


@pytest.fixture(scope="function")
def workflow_zenodo(record_id, workflow: PipelineInstallWorkflow):  # noqa: F811
    workflow.zenodo_id = record_id
    workflow.dpath_pipeline = None
    return workflow


def _assert_files_copied(dpath_source, dpath_dest):
    paths_source = set(
        path.relative_to(dpath_source) for path in dpath_source.rglob("*")
    )
    paths_dest = set(path.relative_to(dpath_dest) for path in dpath_dest.rglob("*"))
    assert paths_source == paths_dest


def test_warning_not_path_or_zenodo(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    PipelineInstallWorkflow(
        dpath_root=(tmp_path / "my_dataset"),
        source="not_a_path",
    )
    assert any(
        [
            "does not seem like a valid path or Zenodo ID" in record.message
            and record.levelno == logging.WARNING
            for record in caplog.records
        ]
    )


@pytest.mark.parametrize("variables", [{}, {"var1": "description"}])
@pytest.mark.parametrize("dry_run", [False, True])
def test_update_config_and_save(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    variables: dict,
    dry_run: bool,
    caplog: pytest.LogCaptureFixture,
):
    pipeline_config.VARIABLES = variables
    workflow.dry_run = dry_run

    new_config = workflow._update_config_and_save(pipeline_config)

    # check that the variables were added to the config file
    assert new_config.PIPELINE_VARIABLES.PROCESSING[pipeline_config.NAME][
        pipeline_config.VERSION
    ] == {variable_name: None for variable_name in variables}

    # check logs
    if variables:
        assert "Adding" in caplog.text
        assert "You must update" in caplog.text
    else:
        assert "Adding" not in caplog.text
        assert "You must update" not in caplog.text


@pytest.mark.parametrize(
    "variables,dry_run", [({}, False), ({"var1": "description"}, True)]
)
def test_update_config_and_save_no_write(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    variables: dict,
    dry_run: bool,
    mocker: pytest_mock.MockFixture,
):
    pipeline_config.VARIABLES = variables
    workflow.dry_run = dry_run

    mocked = mocker.patch.object(Config, "save")

    assert isinstance(workflow._update_config_and_save(pipeline_config), Config)

    # should not update the config file if dry_run is True
    # or if there were no variables to add
    mocked.assert_not_called()


def test_update_config_and_save_no_other_change(
    workflow: PipelineInstallWorkflow, pipeline_config: ProcPipelineConfig
):
    # cache original config
    original_config = Config.load(
        workflow.layout.fpath_config  # , apply_substitutions=False
    )

    # check that placeholder was replaced as expected
    assert original_config != workflow.config
    assert workflow.config.DICOM_DIR_MAP_FILE.parent == workflow.dpath_root

    # create new config file with the new pipeline variables
    pipeline_config.VARIABLES = {"var1": "description"}
    new_config = workflow._update_config_and_save(pipeline_config)

    # check that the new config file is identical to the old one except for
    # the pipeline variables
    assert new_config.model_dump(
        exclude="PIPELINE_VARIABLES"
    ) == original_config.model_dump(exclude="PIPELINE_VARIABLES")


def test_download_container(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
):
    mocked = mocker.patch.object(workflow, "run_command")

    workflow._download_container(pipeline_config)

    # check that the container file was downloaded
    mocked.assert_called_once_with(
        [
            "apptainer",
            "pull",
            workflow.layout.dpath_containers / pipeline_config.CONTAINER_INFO.FILE.name,
            "fake_uri",
        ]
    )


@pytest.mark.parametrize("confirm_download", [True, False])
def test_download_container_confirm_true(
    confirm_download: bool,
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
):
    workflow.assume_yes = False

    mocked_confirm_ask = mocker.patch(
        "nipoppy.workflows.pipeline_store.install.Confirm.ask",
        return_value=confirm_download,
    )

    mocked_run_command = mocker.patch.object(workflow, "run_command")

    workflow._download_container(pipeline_config)
    mocked_confirm_ask.assert_called_once()

    if confirm_download:
        mocked_run_command.assert_called_once()
    else:
        mocked_run_command.assert_not_called()


def test_download_container_status(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
):
    mocked_console = mocker.patch(
        "nipoppy.workflows.pipeline_store.install.Console",
    )
    mocked_status = mocked_console.return_value.status
    mocked_status_update = mocked_status.return_value.__enter__.return_value.update
    mocked_run_command = mocker.patch.object(workflow, "run_command")

    workflow._download_container(pipeline_config)

    mocked_status.assert_called_once_with(
        "Downloading the container, this can take a while..."
    )
    mocked_status_update.assert_called_once()
    assert "Container downloaded to" in mocked_status_update.call_args[0][0]
    mocked_run_command.assert_called_once()


def test_download_container_failed(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    error_message = "Download failed"
    mocked = mocker.patch.object(
        workflow,
        "run_command",
        side_effect=subprocess.CalledProcessError(1, error_message),
    )

    with pytest.raises(SystemExit, match=f"{ReturnCode.UNKNOWN_FAILURE}"):
        workflow._download_container(pipeline_config)

    mocked.assert_called_once()

    last_record = caplog.records[-1]
    assert last_record.levelno == logging.ERROR
    assert "Failed to download container" in last_record.message
    assert error_message in last_record.message


def test_download_container_no_uri(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
):
    pipeline_config.CONTAINER_INFO.URI = None
    mocked = mocker.patch.object(workflow, "run_command")

    workflow._download_container(pipeline_config)

    mocked.assert_not_called()


def test_download_container_image_exists(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    mocker: pytest_mock.MockFixture,
):
    fpath_container = (
        workflow.layout.dpath_containers / pipeline_config.CONTAINER_INFO.FILE.name
    )
    fpath_container.parent.mkdir(parents=True, exist_ok=True)
    fpath_container.touch()
    mocked = mocker.patch.object(workflow, "run_command")

    workflow._download_container(pipeline_config)
    mocked.assert_not_called()


def test_run_main(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    caplog: pytest.LogCaptureFixture,
    mocker: pytest_mock.MockFixture,
):
    dpath_installed = workflow.layout.get_dpath_pipeline_bundle(
        pipeline_config.PIPELINE_TYPE,
        pipeline_config.NAME,
        pipeline_config.VERSION,
    )

    # make sure directory does not already exist
    # also check that the parent directory will be created without error
    assert not dpath_installed.exists()
    assert not dpath_installed.parent.exists()

    # mock
    mocked_update_config_and_save = mocker.patch.object(
        workflow, "_update_config_and_save"
    )
    mocked_download_container = mocker.patch.object(workflow, "_download_container")

    workflow.run_main()
    _assert_files_copied(
        workflow.dpath_pipeline,
        dpath_installed,
    )
    mocked_update_config_and_save.assert_called_once_with(pipeline_config)
    mocked_download_container.assert_called_once_with(pipeline_config)
    assert "Successfully installed pipeline" in caplog.text


@pytest.mark.parametrize("force", [False, True])
def test_run_main_force(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    force: bool,
):
    workflow.force = force

    # create directory where the pipeline is supposed to be installed
    dpath_installed = workflow.layout.get_dpath_pipeline_bundle(
        pipeline_config.PIPELINE_TYPE,
        pipeline_config.NAME,
        pipeline_config.VERSION,
    )
    dpath_installed.mkdir(parents=True)

    with (
        nullcontext()
        if force
        else pytest.raises(FileExistsError, match="Use --force to overwrite")
    ):
        workflow.run_main()
        _assert_files_copied(workflow.dpath_pipeline, dpath_installed)


def test_run_main_invalid_zenodo_record(workflow_zenodo: PipelineInstallWorkflow):
    # https://zenodo.org/records/1482743 is the Boutiques FSL BET descriptor
    workflow_zenodo.zenodo_id = "1482743"
    workflow_zenodo.zenodo_api = ZenodoAPI(sandbox=False)

    with pytest.raises(
        FileNotFoundError,
        match="Pipeline configuration file not found: .* Make sure the record at",
    ):
        workflow_zenodo.run_main()


def test_run_main_file_not_found(workflow: PipelineInstallWorkflow):
    # create a non-existent path
    workflow.dpath_pipeline = workflow.layout.dpath_pipelines / "non_existent_path"
    with pytest.raises(
        FileNotFoundError,
        match="Pipeline configuration file not found: .*/config.json$",
    ):
        workflow.run_main()


def test_download(workflow_zenodo: PipelineInstallWorkflow):

    workflow_zenodo.run_main()

    # Check that the pipeline was downloaded and moved correctly
    assert not (
        workflow_zenodo.layout.dpath_pipelines / workflow_zenodo.zenodo_id
    ).exists()
    assert (
        workflow_zenodo.layout.dpath_pipelines / "processing" / TEST_PIPELINE.name
    ).exists()


@pytest.mark.parametrize("force, fails", [(True, False), (False, True)])
def test_download_dir_exist(
    workflow_zenodo: PipelineInstallWorkflow, force: bool, fails: bool
):
    """Test the behavior when the download directory already exists."""
    workflow_zenodo.force = force

    download_dir = workflow_zenodo.layout.dpath_pipelines / workflow_zenodo.zenodo_id
    download_dir.mkdir(parents=True, exist_ok=True)
    assert download_dir.exists()

    with pytest.raises(SystemExit) if fails else nullcontext():
        workflow_zenodo.run_main()


@pytest.mark.parametrize("force, fails", [(True, False), (False, True)])
def test_download_install_dir_exist(
    workflow_zenodo: PipelineInstallWorkflow, force: bool, fails: bool
):
    workflow_zenodo.force = force

    download_dir = (
        workflow_zenodo.layout.dpath_pipelines / "processing" / TEST_PIPELINE.name
    )
    download_dir.mkdir(parents=True, exist_ok=True)
    assert download_dir.exists()

    with (
        pytest.raises(
            FileExistsError,
            match="Pipeline directory exists: .* Use --force to overwrite",
        )
        if fails
        else nullcontext()
    ):
        workflow_zenodo.run_main()
