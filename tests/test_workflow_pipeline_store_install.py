"""Tests for PipelineInstallWorkflow class."""

from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.main import Config
from nipoppy.config.pipeline import BasePipelineConfig, ProcPipelineConfig
from nipoppy.env import PipelineTypeEnum
from nipoppy.layout import DatasetLayout
from nipoppy.workflows.pipeline_store.install import PipelineInstallWorkflow

from .conftest import create_pipeline_config_files, get_config


@pytest.fixture(scope="function")
def pipeline_config():
    return ProcPipelineConfig(
        **{
            "NAME": "my_pipeline",
            "VERSION": "1.0.0",
            "PIPELINE_TYPE": PipelineTypeEnum.PROCESSING,
        }
    )


@pytest.fixture(scope="function")
def workflow(tmp_path: Path, pipeline_config: ProcPipelineConfig):
    dpath_root = tmp_path / "my_dataset"
    create_pipeline_config_files(
        tmp_path,
        proc_pipelines=[pipeline_config.model_dump()],
    )
    workflow = PipelineInstallWorkflow(
        dpath_root=dpath_root,
        dpath_pipeline=tmp_path
        / DatasetLayout.pipeline_type_to_dname_map[PipelineTypeEnum.PROCESSING]
        / "my_pipeline-1.0.0",
    )
    workflow.config = get_config()
    return workflow


def _check_files_copied(dpath_source, dpath_dest):
    paths_source = set(
        path.relative_to(dpath_source) for path in dpath_source.rglob("*")
    )
    paths_dest = set(path.relative_to(dpath_dest) for path in dpath_dest.rglob("*"))
    assert paths_source == paths_dest


@pytest.mark.parametrize("variables", [{}, {"var1": "description"}])
@pytest.mark.parametrize("dry_run", [False, True])
def test_add_variables_to_config(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    variables: dict,
    dry_run,
    caplog: pytest.LogCaptureFixture,
):
    workflow.dry_run = dry_run
    pipeline_config.VARIABLES = variables
    workflow._add_variables_to_config(pipeline_config)

    if dry_run:
        assert not workflow.layout.fpath_config.exists()
    elif variables:
        # check that the variables were added to the config file
        assert Config.load(workflow.layout.fpath_config).PIPELINE_VARIABLES.PROCESSING[
            pipeline_config.NAME
        ][pipeline_config.VERSION] == {
            variable_name: None for variable_name in variables
        }

        # check logs
        assert "Adding" in caplog.text
        assert "You must update" in caplog.text
    else:
        assert len(caplog.records) == 0


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
    mocked_add_variables_to_config = mocker.patch.object(
        workflow, "_add_variables_to_config"
    )

    workflow.run_main()
    _check_files_copied(
        workflow.dpath_pipeline,
        dpath_installed,
    )
    mocked_add_variables_to_config.assert_called_once_with(
        BasePipelineConfig(**pipeline_config.model_dump())
    )
    assert "Successfully installed pipeline" in caplog.text


@pytest.mark.parametrize("overwrite", [False, True])
def test_run_main_overwrite(
    workflow: PipelineInstallWorkflow,
    pipeline_config: ProcPipelineConfig,
    overwrite: bool,
):
    workflow.overwrite = overwrite

    # create directory where the pipeline is supposed to be installed
    dpath_installed = workflow.layout.get_dpath_pipeline_bundle(
        pipeline_config.PIPELINE_TYPE,
        pipeline_config.NAME,
        pipeline_config.VERSION,
    )
    dpath_installed.mkdir(parents=True)

    with (
        nullcontext()
        if overwrite
        else pytest.raises(FileExistsError, match="Use --overwrite to overwrite")
    ):
        workflow.run_main()
        _check_files_copied(workflow.dpath_pipeline, dpath_installed)
