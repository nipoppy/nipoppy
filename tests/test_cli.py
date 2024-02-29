"""Tests for the CLI."""

from pathlib import Path

import pytest
from conftest import ATTR_TO_DPATH_MAP

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


def test_cli_doughnut(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    try:
        cli(["nipoppy", "doughnut", "--dataset-root", str(dpath_root)])
    except Exception:
        pass

    # check that a logfile was created
    assert (
        len(list((dpath_root / ATTR_TO_DPATH_MAP["dpath_logs"]).glob("doughnut/*.log")))
        == 1
    )
