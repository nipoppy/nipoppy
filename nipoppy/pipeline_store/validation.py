"""Pipeline store functions."""

import json
import logging
from pathlib import Path
from typing import Optional

import boutiques
from pydantic_core import ValidationError

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.config.pipeline_step import ProcPipelineStepConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.layout import DatasetLayout
from nipoppy.utils import StrOrPathLike, load_json


def _load_pipeline_config_file(fpath_config: Path) -> BasePipelineConfig:
    """Load the main pipeline configuration file."""
    fpath_config: Path = Path(fpath_config)
    if not fpath_config.exists():
        raise FileNotFoundError(
            f"Pipeline configuration file not found: {fpath_config}"
        )

    try:
        config_dict = load_json(fpath_config)
    except json.JSONDecodeError as exception:
        raise RuntimeError(
            f"Pipeline configuration file {fpath_config} is not a valid JSON file: "
            f"{exception}"
        )

    try:
        config = BasePipelineConfig(**config_dict)
    except ValidationError as exception:
        raise RuntimeError(
            f"Pipeline configuration file {fpath_config} is invalid:\n{exception}"
        )

    return config


def _check_descriptor_file(fpath_descriptor: StrOrPathLike) -> None:
    """Validate a Boutiques descriptor file."""
    fpath_descriptor: Path = Path(fpath_descriptor)
    if not fpath_descriptor.exists():
        raise FileNotFoundError(f"Descriptor file not found: {fpath_descriptor}")

    try:
        descriptor_dict = load_json(fpath_descriptor)
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"Descriptor file is not a valid JSON file: {exception}")

    descriptor_str = json.dumps(descriptor_dict)
    try:
        boutiques.validate(descriptor_str)
    except boutiques.DescriptorValidationError as exception:
        raise RuntimeError(f"Descriptor file is invalid:\n{exception}")
    return descriptor_str


def _check_invocation_file(fpath_invocation: Path, descriptor_str: str) -> None:
    """Validate a Boutiques invocation file."""
    fpath_invocation: Path = Path(fpath_invocation)
    if not fpath_invocation.exists():
        raise FileNotFoundError(f"Invocation file not found: {fpath_invocation}")

    try:
        invocation_dict = load_json(fpath_invocation)
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"Invocation file is not a valid JSON file: {exception}")

    try:
        boutiques.invocation(
            "--invocation", json.dumps(invocation_dict), descriptor_str
        )
    except boutiques.InvocationValidationError as exception:
        raise RuntimeError(f"Invocation file is invalid:\n{exception}")


def _check_tracker_config_file(fpath_tracker_config: Path) -> None:
    """Validate a tracker config file."""
    fpath_tracker_config: Path = Path(fpath_tracker_config)
    if not fpath_tracker_config.exists():
        raise FileNotFoundError(
            f"Tracker config file not found: {fpath_tracker_config}"
        )

    try:
        tracker_config_dict = load_json(fpath_tracker_config)
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"Tracker config file is not a valid JSON file: {exception}")

    try:
        TrackerConfig(**tracker_config_dict)
    except ValidationError as exception:
        raise RuntimeError(f"Tracker config file is invalid:\n{exception}")


def _check_pybids_ignore_file(fpath_pybids_ignore: Path) -> None:
    """Validate a PyBIDS ignore patterns file."""
    fpath_pybids_ignore: Path = Path(fpath_pybids_ignore)
    if not fpath_pybids_ignore.exists():
        raise FileNotFoundError(
            f"PyBIDS ignore patterns file not found: {fpath_pybids_ignore}"
        )

    try:
        load_json(fpath_pybids_ignore)
    except json.JSONDecodeError as exception:
        raise RuntimeError(
            "PyBIDS ignore patterns file is not a valid JSON file: " f"{exception}"
        )


def _check_pipeline_files(
    pipeline_config: BasePipelineConfig,
    logger: Optional[logging.Logger] = None,
    log_level=logging.DEBUG,
) -> list[Path]:
    """
    Validate the files that the pipeline config points to.

    For each step in the pipeline configuration, validate:

    - the descriptor file (if present)
    - the invocation file (if present)
    - the tracker config file (if present and pipeline is a processing pipeline)
    - the PyBIDS ignore patterns file (if present and pipeline is a processing pipeline)

    Also, collect all file paths for these files for further checks.
    """

    def _log(msg: str) -> None:
        if logger is not None:
            logger.log(level=log_level, msg=msg)

    # collect paths
    fpaths = []

    for step in pipeline_config.STEPS:
        _log(f"Validating files for step: {step.NAME}")

        if step.DESCRIPTOR_FILE is not None:
            _log(f"Checking descriptor file: {step.DESCRIPTOR_FILE}")
            descriptor_str = _check_descriptor_file(step.DESCRIPTOR_FILE)
            fpaths.append(step.DESCRIPTOR_FILE)

            if step.INVOCATION_FILE is not None:
                _log(f"Checking invocation file: {step.INVOCATION_FILE}")
                _check_invocation_file(step.INVOCATION_FILE, descriptor_str)
                fpaths.append(step.INVOCATION_FILE)

        if isinstance(step, ProcPipelineStepConfig):

            if step.TRACKER_CONFIG_FILE is not None:
                _log(f"Checking tracker config file: {step.TRACKER_CONFIG_FILE}")
                _check_tracker_config_file(step.TRACKER_CONFIG_FILE)
                fpaths.append(step.TRACKER_CONFIG_FILE)

            if step.PYBIDS_IGNORE_FILE is not None:
                _log(f"Checking PyBIDS ignore patterns file: {step.PYBIDS_IGNORE_FILE}")
                _check_pybids_ignore_file(step.PYBIDS_IGNORE_FILE)
                fpaths.append(step.PYBIDS_IGNORE_FILE)

    return fpaths


def _check_self_contained(
    dpath_bundle: StrOrPathLike,
    fpaths: list[StrOrPathLike],
    logger: Optional[logging.Logger] = None,
    log_level=logging.DEBUG,
) -> None:
    """Check that all files are within the bundle directory."""
    dpath_bundle: Path = Path(dpath_bundle).resolve()
    if logger is not None:
        logger.log(
            level=log_level,
            msg=(
                "Checking that all files are within the bundle directory"
                f" {dpath_bundle}"
            ),
        )
    for fpath in fpaths:
        if not any(
            [
                dpath_parent.resolve() == dpath_bundle
                for dpath_parent in Path(fpath).parents
            ]
        ):
            raise ValueError(
                f"Path {fpath} is not within the bundle directory {dpath_bundle}"
            )


def check_pipeline_bundle(
    dpath_bundle: StrOrPathLike,
    logger: Optional[logging.Logger] = None,
    log_level=logging.DEBUG,
) -> BasePipelineConfig:
    """Load a pipeline bundle's main configuration file and validate it."""
    dpath_bundle = Path(dpath_bundle).resolve()
    fpath_config: Path = dpath_bundle / DatasetLayout.fname_pipeline_config

    # try to load the configuration file
    config = _load_pipeline_config_file(fpath_config)

    # core file content validation
    fpaths = _check_pipeline_files(config, logger=logger, log_level=log_level)

    # make sure that all files are within the bundle directory
    _check_self_contained(dpath_bundle, fpaths, logger=logger, log_level=log_level)

    return config
