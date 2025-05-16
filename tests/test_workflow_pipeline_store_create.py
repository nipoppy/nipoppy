import json
from pathlib import Path

import pytest

from nipoppy.env import TEMPLATE_PIPELINE_PATH, PipelineTypeEnum
from nipoppy.workflows.pipeline_store.create import (
    PipelineCreateWorkflow,
)
from tests.conftest import TEST_PIPELINE


@pytest.fixture(scope="function")
def target(tmp_path: Path) -> Path:
    """Fixture to provide a target directory for the tests."""
    return tmp_path / "target"


@pytest.mark.parametrize(
    "type_",
    [
        PipelineTypeEnum.BIDSIFICATION,
        PipelineTypeEnum.PROCESSING,
        PipelineTypeEnum.EXTRACTION,
    ],
)
def test_create(target: Path, type_: PipelineTypeEnum):
    """Test the creation of a pipeline bundle."""
    assert not target.exists()

    # Run the workflow
    PipelineCreateWorkflow(
        target=target,
        type_=type_,
    ).run_main()

    # Check the bundle content exists and is correct
    assert target.joinpath("descriptor.json").is_file()
    assert (
        target.joinpath("descriptor.json").read_text().strip()
        == TEMPLATE_PIPELINE_PATH.joinpath("descriptor.json").read_text().strip()
    )

    assert target.joinpath("invocation.json").is_file()
    # Cannot compare the content of the invocation.json file
    # because boutiques generates random args values.
    # Instead, we compare the keys of the JSON object
    assert (
        json.loads(target.joinpath("invocation.json").read_text()).keys()
        == json.loads(
            TEMPLATE_PIPELINE_PATH.joinpath("invocation.json").read_text()
        ).keys()
    )

    assert target.joinpath("hpc.json").is_file()
    assert (
        target.joinpath("hpc.json").read_text().strip()
        == TEMPLATE_PIPELINE_PATH.joinpath("hpc.json").read_text().strip()
    )

    assert target.joinpath("zenodo.json").is_file()
    assert (
        target.joinpath("zenodo.json").read_text().strip()
        == TEMPLATE_PIPELINE_PATH.joinpath("zenodo.json").read_text().strip()
    )

    assert target.joinpath("config.json").is_file()
    assert (
        target.joinpath("config.json").read_text().strip()
        == TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json")
        .read_text()
        .strip()
    )

    if type_ == PipelineTypeEnum.PROCESSING:
        assert target.joinpath("tracker.json").is_file()
        assert (
            target.joinpath("tracker.json").read_text().strip()
            == TEMPLATE_PIPELINE_PATH.joinpath("tracker.json").read_text().strip()
        )


def test_create_already_exists(target: Path):
    """Test the behavior when the target directory already exists."""
    target.mkdir(parents=True, exist_ok=True)
    assert target.exists()

    with pytest.raises(IsADirectoryError, match="Target directory .* already exists"):
        PipelineCreateWorkflow(
            target=target,
            type_=PipelineTypeEnum.PROCESSING,
        ).run_main()


def test_create_from_descriptor(target: Path):
    """Test the behavior when the bundle is created from a descriptor."""
    source_descriptor = TEST_PIPELINE / "descriptor.json"

    PipelineCreateWorkflow(
        target=target,
        type_=PipelineTypeEnum.PROCESSING,
        source_descriptor=source_descriptor,
    ).run_main()

    assert (
        target.joinpath("descriptor.json").read_text().strip()
        == source_descriptor.read_text().strip()
    )

    assert set(json.loads(target.joinpath("invocation.json").read_text()).keys()) == {
        "bids_dir",
        "output_dir",
        "analysis_level",
    }

    descriptor = json.loads(target.joinpath("descriptor.json").read_text())
    config = json.loads(target.joinpath("config.json").read_text())
    assert config["NAME"] == descriptor["name"]
    assert config["VERSION"] == descriptor["tool-version"]
