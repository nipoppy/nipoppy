"""Tests for the CLI."""
import pytest

from nipoppy.cli.run import cli


def test_cli():
    """Smoke test."""
    with pytest.raises(SystemExit) as exception:
        cli(["nipoppy", "-h"])
    assert exception.value.code == 0


def test_cli_invalid():
    """Check that invalid arguments raise error."""
    with pytest.raises(SystemExit) as exception:
        cli(["nipoppy", "--fake-arg"])
    assert exception.value.code != 0
