"""Tests for PipelineCreateWorkflow class."""

from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import FileOperationError, WorkflowError
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.utils.utils import TEMPLATE_PIPELINE_PATH, load_json
from nipoppy.workflows.pipeline_store import create as create_module
from nipoppy.workflows.pipeline_store.create import (
    PipelineCreateWorkflow,
)
from tests.conftest import TEST_PIPELINE


def _has_same_content(a: Path, b: Path) -> bool:
    """Check if two files are the same."""
    return a.read_text().strip() == b.read_text().strip()


@pytest.fixture(scope="function")
def target(tmp_path: Path) -> Path:
    """Fixture to provide a target directory for the tests."""
    return tmp_path / "target"


@pytest.fixture(scope="function")
def workflow(target: Path) -> PipelineCreateWorkflow:
    """Fixture to provide a PipelineCreateWorkflow instance for the tests."""
    return PipelineCreateWorkflow(
        pipeline_dir=target,
        type_=PipelineTypeEnum.PROCESSING,
    )


@pytest.mark.parametrize(
    "type_",
    [
        PipelineTypeEnum.BIDSIFICATION,
        PipelineTypeEnum.PROCESSING,
        PipelineTypeEnum.EXTRACTION,
    ],
)
def test_create(workflow: PipelineCreateWorkflow, type_: PipelineTypeEnum):
    """Test the creation of a pipeline bundle."""
    assert not workflow.pipeline_dir.exists()

    # Run the workflow
    workflow.type_ = type_
    workflow.run_main()

    check_pipeline_bundle(workflow.pipeline_dir)

    # Check the bundle content exists and is correct
    assert workflow.pipeline_dir.joinpath("descriptor.json").is_file()
    assert _has_same_content(
        workflow.pipeline_dir.joinpath("descriptor.json"),
        TEMPLATE_PIPELINE_PATH.joinpath("descriptor.json"),
    )

    assert workflow.pipeline_dir.joinpath("invocation.json").is_file()
    # Cannot compare the content of the invocation.json file
    # because boutiques generates random args values.
    # Instead, we compare the keys of the JSON object
    assert (
        load_json(workflow.pipeline_dir.joinpath("invocation.json")).keys()
        == load_json(TEMPLATE_PIPELINE_PATH.joinpath("invocation.json")).keys()
    )

    assert workflow.pipeline_dir.joinpath("hpc.json").is_file()
    assert _has_same_content(
        workflow.pipeline_dir.joinpath("hpc.json"),
        TEMPLATE_PIPELINE_PATH.joinpath("hpc.json"),
    )

    assert workflow.pipeline_dir.joinpath("config.json").is_file()
    assert _has_same_content(
        workflow.pipeline_dir.joinpath("config.json"),
        TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json"),
    )

    if type_ == PipelineTypeEnum.PROCESSING:
        assert workflow.pipeline_dir.joinpath("tracker.json").is_file()
        assert _has_same_content(
            workflow.pipeline_dir.joinpath("tracker.json"),
            TEMPLATE_PIPELINE_PATH.joinpath("tracker.json"),
        )


def test_create_already_exists(workflow: PipelineCreateWorkflow):
    """Test the behavior when the target directory already exists."""
    workflow.pipeline_dir.mkdir(parents=True, exist_ok=True)
    assert workflow.pipeline_dir.exists()

    with pytest.raises(FileOperationError, match="Target directory .* already exists"):
        workflow.run_main()


def test_create_from_descriptor(workflow: PipelineCreateWorkflow):
    """Test the behavior when the bundle is created from a descriptor."""
    source_descriptor = TEST_PIPELINE / "descriptor.json"

    workflow.source_descriptor = source_descriptor
    workflow.run_main()

    check_pipeline_bundle(workflow.pipeline_dir)

    assert _has_same_content(
        workflow.pipeline_dir.joinpath("descriptor.json"), source_descriptor
    )

    assert set(load_json(workflow.pipeline_dir.joinpath("invocation.json")).keys()) == {
        "bids_dir",
        "output_dir",
        "analysis_level",
    }

    descriptor = load_json(workflow.pipeline_dir.joinpath("descriptor.json"))
    config = load_json(workflow.pipeline_dir.joinpath("config.json"))
    assert config["NAME"] == descriptor["name"]
    assert config["VERSION"] == descriptor["tool-version"]
    assert (
        config["CONTAINER_INFO"]["URI"]
        == "docker://nipreps/[[PIPELINE_NAME]]:[[PIPELINE_VERSION]]"
    )


def test_create_from_descriptor_preserves_jsonc(
    tmp_path: Path,
    workflow: PipelineCreateWorkflow,
    monkeypatch: pytest.MonkeyPatch,
):
    dpath_template = tmp_path / "template_pipeline"
    dpath_template.mkdir(parents=True)

    (dpath_template / "config-processing.json").write_text("""
{
  // keep this comment
  "NAME": "tool name",
  "VERSION": "v0.1.0",
  "CONTAINER_INFO": {
    "URI": "docker://<OWNER>/[[PIPELINE_NAME]]:[[PIPELINE_VERSION]]",
  },
  "CONTAINER_CONFIG": {
    "ENV_VARS": {},
    "ARGS": [],
  },
  "STEPS": [
    {
      "INVOCATION_FILE": "invocation.json",
      "DESCRIPTOR_FILE": "descriptor.json",
      "ANALYSIS_LEVEL": "participant_session",
      "TRACKER_CONFIG_FILE": "tracker.json",
      "HPC_CONFIG_FILE": "hpc.json",
      "GENERATE_PYBIDS_DATABASE": false,
      "PYBIDS_IGNORE_FILE": null,
    },
  ],
  "PIPELINE_TYPE": "processing",
  "SCHEMA_VERSION": "1",
}
""".strip())
    (dpath_template / "hpc.json").write_text("{}")
    (dpath_template / "tracker.json").write_text("{}")

    monkeypatch.setattr(create_module, "TEMPLATE_PIPELINE_PATH", dpath_template)

    workflow.source_descriptor = TEST_PIPELINE / "descriptor.json"
    workflow.run_main()

    config_text = workflow.pipeline_dir.joinpath("config.json").read_text()
    assert "// keep this comment" in config_text
    assert '"NAME": "fmriprep"' in config_text
    assert '"VERSION": "24.1.1"' in config_text


@pytest.mark.parametrize(
    "file_content,exception_message",
    [
        ("", "Error validating the descriptor file .*:"),
        ("{}", "Descriptor file .* is invalid:"),
    ],
)
def test_create_invalid_descriptor(
    tmp_path: Path,
    workflow: PipelineCreateWorkflow,
    file_content: str,
    exception_message: str,
):
    """Test the behavior when the source descriptor is invalid."""
    source_descriptor = tmp_path / "bad_descriptor.json"
    source_descriptor.write_text(file_content)

    workflow.source_descriptor = source_descriptor

    with pytest.raises(WorkflowError, match=exception_message):
        workflow.run_main()
