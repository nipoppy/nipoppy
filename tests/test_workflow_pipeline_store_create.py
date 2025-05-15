from pathlib import Path

import pytest

from nipoppy.workflows.pipeline_store.create import (
    PipelineCreateWorkflow,
)
from tests.conftest import DPATH_TEST_DATA

TEMPLATE_BUNDLE = DPATH_TEST_DATA / "template_pipeline_bundle"


@pytest.fixture(scope="function")
def target(tmp_path: Path) -> Path:
    """Fixture to provide a target directory for the tests."""
    return tmp_path / "target"


def test_create(target: Path):
    """Test the creation of a pipeline bundle."""
    assert not target.exists()

    # Run the workflow
    PipelineCreateWorkflow(
        target=target,
    ).run_main()

    # Check the bundle content exists and is correct
    assert target.joinpath("descriptor.json").is_file()
    assert (
        target.joinpath("descriptor.json").read_text()
        == TEMPLATE_BUNDLE.joinpath("descriptor.json").read_text()
    )

    assert target.joinpath("invocation.json").is_file()
    # Cannot compare the content of the invocation.json file
    # because boutiques generates random args values

    assert target.joinpath("tracker.json").is_file()
    assert (
        target.joinpath("tracker.json").read_text()
        == TEMPLATE_BUNDLE.joinpath("tracker.json").read_text()
    )

    assert target.joinpath("config.json").is_file()
    assert (
        target.joinpath("config.json").read_text()
        == TEMPLATE_BUNDLE.joinpath("config.json").read_text()
    )


def test_create_already_exists(target: Path):
    """Test the behavior when the target directory already exists."""
    target.mkdir(parents=True, exist_ok=True)
    assert target.exists()

    with pytest.raises(IsADirectoryError, match="Target directory .* already exists"):
        PipelineCreateWorkflow(
            target=target,
        ).run_main()


@pytest.mark.skip(reason="Not implemented yet")
def test_create_from_descriptor(target: Path):
    """Test the behavior when the bundle is created from a descriptor."""
    ...
