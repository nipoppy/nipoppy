"""Pipeline store functions."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

import boutiques
from pydantic_core import ValidationError

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.config.pipeline_step import ProcPipelineStepConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import StrOrPathLike
from nipoppy.layout import DatasetLayout
from nipoppy.utils import load_json, process_template_str


def _load_pipeline_config_file(
    fpath_config: Path, substitution_objs: Optional[list[Any]] = None
) -> BasePipelineConfig:
    """Load the main pipeline configuration file."""
    fpath_config: Path = Path(fpath_config)
    if not fpath_config.exists():
        raise FileNotFoundError(
            f"Pipeline configuration file not found: {fpath_config}"
        )

    config_str = process_template_str(
        fpath_config.read_text(),
        objs=substitution_objs,
    )

    try:
        config_dict = json.loads(config_str)
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
    dpath_bundle: StrOrPathLike,
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

    dpath_bundle = Path(dpath_bundle)

    # collect paths
    fpaths = []

    for step in pipeline_config.STEPS:
        _log(f"Validating files for step: {step.NAME}")

        if step.DESCRIPTOR_FILE is not None:
            _log(f"\tChecking descriptor file: {step.DESCRIPTOR_FILE}")
            fpath_descriptor = dpath_bundle / step.DESCRIPTOR_FILE
            descriptor_str = _check_descriptor_file(fpath_descriptor)
            fpaths.append(fpath_descriptor)

            if step.INVOCATION_FILE is not None:
                _log(f"\tChecking invocation file: {step.INVOCATION_FILE}")
                fpath_invocation = dpath_bundle / step.INVOCATION_FILE
                _check_invocation_file(fpath_invocation, descriptor_str)
                fpaths.append(fpath_invocation)

        if isinstance(step, ProcPipelineStepConfig):

            if step.TRACKER_CONFIG_FILE is not None:
                _log(f"\tChecking tracker config file: {step.TRACKER_CONFIG_FILE}")
                fpath_tracker_config = dpath_bundle / step.TRACKER_CONFIG_FILE
                _check_tracker_config_file(fpath_tracker_config)
                fpaths.append(fpath_tracker_config)

            if step.PYBIDS_IGNORE_FILE is not None:
                _log(
                    f"\tChecking PyBIDS ignore patterns file: {step.PYBIDS_IGNORE_FILE}"
                )
                fpath_pybids_ignore = dpath_bundle / step.PYBIDS_IGNORE_FILE
                _check_pybids_ignore_file(fpath_pybids_ignore)
                fpaths.append(fpath_pybids_ignore)

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
    substitution_objs: Optional[list[Any]] = None,
    logger: Optional[logging.Logger] = None,
    log_level=logging.DEBUG,
) -> BasePipelineConfig:
    """Load a pipeline bundle's main configuration file and validate it."""
    dpath_bundle = Path(dpath_bundle).resolve()
    fpath_config: Path = dpath_bundle / DatasetLayout.fname_pipeline_config

    # try to load the configuration file
    config = _load_pipeline_config_file(fpath_config, substitution_objs)

    # core file content validation
    fpaths = _check_pipeline_files(
        config, dpath_bundle, logger=logger, log_level=log_level
    )

    # make sure that all files are within the bundle directory
    _check_self_contained(dpath_bundle, fpaths, logger=logger, log_level=log_level)

    return config
