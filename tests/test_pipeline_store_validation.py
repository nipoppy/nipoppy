"""Tests for the nipoppy.pipeline_store.validation module."""

import logging
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.pipeline import (
    BasePipelineConfig,
    BidsPipelineConfig,
    ExtractionPipelineConfig,
    ProcPipelineConfig,
)
from nipoppy.env import PipelineTypeEnum
from nipoppy.layout import DatasetLayout
from nipoppy.pipeline_store.validation import (
    _check_descriptor_file,
    _check_invocation_file,
    _check_pipeline_files,
    _check_pybids_ignore_file,
    _check_self_contained,
    _check_tracker_config_file,
    _load_pipeline_config_file,
    check_pipeline_bundle,
)

from .conftest import DPATH_TEST_DATA


@pytest.fixture()
def descriptor_str():
    """Fixture for _check_invocation_file."""
    return Path(DPATH_TEST_DATA / "descriptor-valid.json").read_text()


def test_load_pipeline_config_file():
    assert isinstance(
        _load_pipeline_config_file(DPATH_TEST_DATA / "pipeline_config-valid.json"),
        BasePipelineConfig,
    )


@pytest.mark.parametrize(
    "substitution_objs,expected_description",
    [
        ([DatasetLayout("/test")], "/test"),
        ([DatasetLayout("/test2")], "/test2"),
    ],
)
def test_load_pipeline_config_file_substitutions(
    substitution_objs, expected_description, tmp_path: Path
):
    config_to_write = BasePipelineConfig(
        NAME="test", VERSION="0.0.1", DESCRIPTION="[[NIPOPPY_DPATH_ROOT]]"
    )
    fpath_pipeline_config = tmp_path / "pipeline_config.json"
    fpath_pipeline_config.write_text(config_to_write.model_dump_json(indent=4))
    pipeline_config = _load_pipeline_config_file(
        fpath_pipeline_config, substitution_objs
    )
    assert pipeline_config.DESCRIPTION == expected_description


@pytest.mark.parametrize(
    "fpath,exception_class,exception_message",
    [
        ("fake_path.json", FileNotFoundError, "Pipeline configuration file not found"),
        (
            DPATH_TEST_DATA / "empty_file.txt",
            RuntimeError,
            "Pipeline configuration file .* is not a valid JSON file",
        ),
        (
            DPATH_TEST_DATA / "pipeline_config-invalid.json",
            RuntimeError,
            "Pipeline configuration file .* is invalid",
        ),
    ],
)
def test_load_pipeline_config_file_invalid(fpath, exception_class, exception_message):
    with pytest.raises(exception_class, match=exception_message):
        _load_pipeline_config_file(fpath)


def test_check_descriptor_file():
    assert isinstance(
        _check_descriptor_file(DPATH_TEST_DATA / "descriptor-valid.json"), str
    )


@pytest.mark.parametrize(
    "fpath,exception_class,exception_message",
    [
        ("fake_path.json", FileNotFoundError, "Descriptor file not found"),
        (
            DPATH_TEST_DATA / "empty_file.txt",
            RuntimeError,
            "Descriptor file is not a valid JSON file",
        ),
        (
            DPATH_TEST_DATA / "descriptor-invalid.json",
            RuntimeError,
            "Descriptor file .* is invalid",
        ),
    ],
)
def test_check_descriptor_file_invalid(fpath, exception_class, exception_message):
    with pytest.raises(exception_class, match=exception_message):
        _check_descriptor_file(fpath)


def test_check_invocation_file(descriptor_str):
    _check_invocation_file(DPATH_TEST_DATA / "invocation-valid.json", descriptor_str)


@pytest.mark.parametrize(
    "fpath,exception_class,exception_message",
    [
        ("fake_path.json", FileNotFoundError, "Invocation file not found"),
        (
            DPATH_TEST_DATA / "empty_file.txt",
            RuntimeError,
            "Invocation file is not a valid JSON file",
        ),
        (
            DPATH_TEST_DATA / "invocation-invalid.json",
            RuntimeError,
            "Invocation file .* is invalid",
        ),
    ],
)
def test_check_invocation_file_invalid(
    fpath, exception_class, exception_message, descriptor_str
):
    with pytest.raises(exception_class, match=exception_message):
        _check_invocation_file(fpath, descriptor_str)


def test_check_tracker_config_file():
    _check_tracker_config_file(DPATH_TEST_DATA / "tracker_config-valid.json")


@pytest.mark.parametrize(
    "fpath,exception_class,exception_message",
    [
        ("fake_path.json", FileNotFoundError, "Tracker config file not found"),
        (
            DPATH_TEST_DATA / "empty_file.txt",
            RuntimeError,
            "Tracker config file is not a valid JSON file",
        ),
        (
            DPATH_TEST_DATA / "tracker_config-invalid.json",
            RuntimeError,
            "Tracker config file .* is invalid",
        ),
    ],
)
def test_check_tracker_config_file_invalid(fpath, exception_class, exception_message):
    with pytest.raises(exception_class, match=exception_message):
        _check_tracker_config_file(fpath)


def test_check_pybids_ignore_file():
    _check_pybids_ignore_file(DPATH_TEST_DATA / "pybids_ignore-valid.json")


@pytest.mark.parametrize(
    "fpath,exception_class,exception_message",
    [
        ("fake_path.json", FileNotFoundError, "PyBIDS ignore patterns file not found"),
        (
            DPATH_TEST_DATA / "empty_file.txt",
            RuntimeError,
            "PyBIDS ignore patterns file is not a valid JSON file",
        ),
    ],
)
def test_check_pybids_ignore_file_invalid(fpath, exception_class, exception_message):
    with pytest.raises(exception_class, match=exception_message):
        _check_pybids_ignore_file(fpath)


@pytest.mark.parametrize(
    "pipeline_config_data,pipeline_class,n_files_expected",
    [
        ({"STEPS": [{}]}, BasePipelineConfig, 0),
        (
            {
                "STEPS": [
                    {
                        "INVOCATION_FILE": "invocation-valid.json",
                        "DESCRIPTOR_FILE": "descriptor-valid.json",
                    },
                ],
                "PIPELINE_TYPE": PipelineTypeEnum.BIDSIFICATION,
            },
            BidsPipelineConfig,
            2,
        ),
        (
            {
                "STEPS": [
                    {
                        "INVOCATION_FILE": "invocation-valid.json",
                        "DESCRIPTOR_FILE": "descriptor-valid.json",
                        "TRACKER_CONFIG_FILE": "tracker_config-valid.json",
                        "PYBIDS_IGNORE_FILE": "pybids_ignore-valid.json",
                    },
                ],
                "PIPELINE_TYPE": PipelineTypeEnum.PROCESSING,
            },
            ProcPipelineConfig,
            4,
        ),
        (
            {
                "PROC_DEPENDENCIES": [{"NAME": "test", "VERSION": "v1"}],
                "STEPS": [
                    {
                        "NAME": "step1",
                        "INVOCATION_FILE": "invocation-valid.json",
                        "DESCRIPTOR_FILE": "descriptor-valid.json",
                    },
                    {
                        "NAME": "step2",
                        "INVOCATION_FILE": "invocation-valid.json",
                        "DESCRIPTOR_FILE": "descriptor-valid.json",
                    },
                    {
                        "NAME": "step3",
                        "INVOCATION_FILE": "invocation-valid.json",
                        "DESCRIPTOR_FILE": "descriptor-valid.json",
                    },
                ],
                "PIPELINE_TYPE": PipelineTypeEnum.EXTRACTION,
            },
            ExtractionPipelineConfig,
            6,
        ),
    ],
)
def test_check_config_files(pipeline_config_data, pipeline_class, n_files_expected):

    pipeline_config = pipeline_class(
        **pipeline_config_data, NAME="test_pipeline", VERSION="test_version"
    )
    files = _check_pipeline_files(pipeline_config, DPATH_TEST_DATA)

    # check that the function returns the expected number of files
    assert isinstance(files, list)
    assert n_files_expected == len(files)


@pytest.mark.parametrize(
    "logger,log_level",
    [
        (None, logging.DEBUG),
        (logging.getLogger("test"), logging.DEBUG),
        (logging.getLogger("test"), logging.INFO),
    ],
)
def test_check_config_files_logging(
    logger,
    log_level,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(log_level)

    pipeline_config = BasePipelineConfig(
        NAME="test_pipeline", VERSION="test_version", STEPS=[{}]
    )
    _check_pipeline_files(
        pipeline_config, DPATH_TEST_DATA, logger=logger, log_level=log_level
    )

    if logger is None:
        assert len(caplog.records) == 0
    else:
        assert len(caplog.records) > 0
        assert all([record.levelno == log_level for record in caplog.records])


@pytest.mark.parametrize(
    "dpath_bundle,fpaths,valid",
    [
        ("bundle_dir", ["bundle_dir/file1.txt", "bundle_dir/file2.txt"], True),
        ("bundle_dir", ["bundle_dir/file1.txt", "bundle_dir/sub_dir/file2.txt"], True),
        ("bundle_dir", ["bundle_dir/file1.txt", "file2.txt"], False),
        ("bundle_dir", ["bundle_dir/file1.txt", "other_dir/file2.txt"], False),
    ],
)
def test_check_self_contained(dpath_bundle, fpaths, valid):
    with (
        nullcontext()
        if valid
        else pytest.raises(
            ValueError, match="Path .* is not within the bundle directory"
        )
    ):
        _check_self_contained(dpath_bundle, fpaths)


@pytest.mark.parametrize(
    "logger,log_level",
    [
        (None, logging.DEBUG),
        (logging.getLogger("test"), logging.DEBUG),
        (logging.getLogger("test"), logging.INFO),
    ],
)
def test_check_self_container_logging(
    logger, log_level, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(log_level)

    dpath_bundle = "bundle_dir"
    fpaths = ["bundle_dir/file1.txt", "bundle_dir/file2.txt"]
    _check_self_contained(dpath_bundle, fpaths, logger=logger, log_level=log_level)

    if logger is None:
        assert len(caplog.records) == 0
    else:
        assert len(caplog.records) > 0
        assert all([record.levelno == log_level for record in caplog.records])


@pytest.mark.parametrize(
    "logger,log_level",
    [(None, logging.DEBUG), (logging.getLogger("test"), logging.INFO)],
)
def test_check_pipeline_bundle(logger, log_level, mocker: pytest_mock.MockFixture):
    dpath_bundle = Path("bundle_dir").resolve()
    substitution_objs = [dpath_bundle]
    config = BasePipelineConfig(NAME="test_pipeline", VERSION="test_version")
    fpaths = [dpath_bundle / "file1.txt", dpath_bundle / "file2.txt"]

    mocked_load_pipeline_config_file = mocker.patch(
        "nipoppy.pipeline_store.validation._load_pipeline_config_file",
        return_value=config,
    )
    mocked_check_pipeline_files = mocker.patch(
        "nipoppy.pipeline_store.validation._check_pipeline_files",
        return_value=fpaths,
    )
    mocked_check_self_contained = mocker.patch(
        "nipoppy.pipeline_store.validation._check_self_contained"
    )

    check_pipeline_bundle(
        dpath_bundle, substitution_objs, logger=logger, log_level=log_level
    )

    mocked_load_pipeline_config_file.assert_called_once_with(
        dpath_bundle / "config.json",
        substitution_objs,
    )
    mocked_check_pipeline_files.assert_called_once_with(
        config, dpath_bundle, logger=logger, log_level=log_level
    )
    mocked_check_self_contained.assert_called_once_with(
        dpath_bundle, fpaths, logger=logger, log_level=log_level
    )
