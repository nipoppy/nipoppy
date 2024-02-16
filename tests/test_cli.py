"""Tests for the CLI."""

from pathlib import Path

import pytest

from nipoppy.cli.run import cli


def test_cli():
    with pytest.raises(SystemExit) as exception:
        cli(["nipoppy", "-h"])
    assert exception.value.code == 0


def test_cli_invalid():
    with pytest.raises(SystemExit) as exception:
        cli(["nipoppy", "--fake-arg"])
    assert exception.value.code != 0


def test_cli_init(tmp_path: Path):
    assert (
        cli(["nipoppy", "init", "--dataset-root", str(tmp_path / "my_dataset")]) is None
    )
