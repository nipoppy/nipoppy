"""Tests for PipelineInstallWorkflow class."""

from contextlib import nullcontext
from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
from nipoppy.layout import DatasetLayout
from nipoppy.workflows.pipeline_store.install import PipelineInstallWorkflow

from .conftest import create_empty_dataset, create_pipeline_config_files


@pytest.fixture()
def pipeline_config():
    return {
        "NAME": "my_pipeline",
        "VERSION": "1.0.0",
        "PIPELINE_TYPE": PipelineTypeEnum.PROCESSING,
    }


@pytest.fixture(scope="function")
def workflow(tmp_path: Path, pipeline_config: dict):
    dpath_root = tmp_path / "my_dataset"
    create_empty_dataset(dpath_root)
    create_pipeline_config_files(
        tmp_path,
        proc_pipelines=[pipeline_config],
    )
    workflow = PipelineInstallWorkflow(
        dpath_root=dpath_root,
        dpath_pipeline=tmp_path
        / DatasetLayout.pipeline_type_to_dname_map[PipelineTypeEnum.PROCESSING]
        / "my_pipeline-1.0.0",
    )
    return workflow


def _check_files_copied(dpath_source, dpath_dest):
    paths_source = set(
        path.relative_to(dpath_source) for path in dpath_source.rglob("*")
    )
    paths_dest = set(path.relative_to(dpath_dest) for path in dpath_dest.rglob("*"))
    assert paths_source == paths_dest


def test_run_main(
    workflow: PipelineInstallWorkflow,
    pipeline_config: dict,
    caplog: pytest.LogCaptureFixture,
):
    dpath_installed = workflow.layout.get_dpath_pipeline_bundle(
        pipeline_config["PIPELINE_TYPE"],
        pipeline_config["NAME"],
        pipeline_config["VERSION"],
    )

    # make sure directory does not already exist
    # also check that the parent directory will be created without error
    assert not dpath_installed.exists()
    assert not dpath_installed.parent.exists()

    workflow.run_main()
    _check_files_copied(
        workflow.dpath_pipeline,
        dpath_installed,
    )
    assert "Successfully installed pipeline" in caplog.text


@pytest.mark.parametrize("overwrite", [False, True])
def test_run_main_overwrite(
    workflow: PipelineInstallWorkflow, pipeline_config: dict, overwrite: bool
):
    workflow.overwrite = overwrite

    # create directory where the pipeline is supposed to be installed
    dpath_installed = workflow.layout.get_dpath_pipeline_bundle(
        pipeline_config["PIPELINE_TYPE"],
        pipeline_config["NAME"],
        pipeline_config["VERSION"],
    )
    dpath_installed.mkdir(parents=True)

    with (
        nullcontext()
        if overwrite
        else pytest.raises(FileExistsError, match="Use --overwrite to overwrite")
    ):
        workflow.run_main()
        _check_files_copied(workflow.dpath_pipeline, dpath_installed)
