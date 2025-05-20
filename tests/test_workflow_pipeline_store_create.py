from pathlib import Path

import pytest

from nipoppy.env import PipelineTypeEnum
from nipoppy.pipeline_validation import check_pipeline_bundle
from nipoppy.utils import TEMPLATE_PIPELINE_PATH, load_json
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
        pipeline_dir=target,
        type_=type_,
    ).run_main()

    check_pipeline_bundle(target)

    # Check the bundle content exists and is correct
    assert target.joinpath("descriptor.json").is_file()
    assert _has_same_content(
        target.joinpath("descriptor.json"),
        TEMPLATE_PIPELINE_PATH.joinpath("descriptor.json"),
    )

    assert target.joinpath("invocation.json").is_file()
    # Cannot compare the content of the invocation.json file
    # because boutiques generates random args values.
    # Instead, we compare the keys of the JSON object
    assert (
        load_json(target.joinpath("invocation.json")).keys()
        == load_json(TEMPLATE_PIPELINE_PATH.joinpath("invocation.json")).keys()
    )

    assert target.joinpath("hpc.json").is_file()
    assert _has_same_content(
        target.joinpath("hpc.json"), TEMPLATE_PIPELINE_PATH.joinpath("hpc.json")
    )

    assert target.joinpath("config.json").is_file()
    assert _has_same_content(
        target.joinpath("config.json"),
        TEMPLATE_PIPELINE_PATH.joinpath(f"config-{type_.value}.json"),
    )

    if type_ == PipelineTypeEnum.PROCESSING:
        assert target.joinpath("tracker.json").is_file()
        assert _has_same_content(
            target.joinpath("tracker.json"),
            TEMPLATE_PIPELINE_PATH.joinpath("tracker.json"),
        )


def test_create_already_exists(target: Path):
    """Test the behavior when the target directory already exists."""
    target.mkdir(parents=True, exist_ok=True)
    assert target.exists()

    with pytest.raises(IsADirectoryError, match="Target directory .* already exists"):
        PipelineCreateWorkflow(
            pipeline_dir=target,
            type_=PipelineTypeEnum.PROCESSING,
        ).run_main()


def test_create_from_descriptor(target: Path):
    """Test the behavior when the bundle is created from a descriptor."""
    source_descriptor = TEST_PIPELINE / "descriptor.json"

    PipelineCreateWorkflow(
        pipeline_dir=target,
        type_=PipelineTypeEnum.PROCESSING,
        source_descriptor=source_descriptor,
    ).run_main()

    check_pipeline_bundle(target)

    assert _has_same_content(target.joinpath("descriptor.json"), source_descriptor)

    assert set(load_json(target.joinpath("invocation.json")).keys()) == {
        "bids_dir",
        "output_dir",
        "analysis_level",
    }

    descriptor = load_json(target.joinpath("descriptor.json"))
    config = load_json(target.joinpath("config.json"))
    assert config["NAME"] == descriptor["name"]
    assert config["VERSION"] == descriptor["tool-version"]
