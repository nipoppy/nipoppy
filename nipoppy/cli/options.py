"""Define shared Click options for the Nipoppy CLI."""

import os
from pathlib import Path

import rich_click as click

from nipoppy.cli import logger
from nipoppy.env import BIDS_SESSION_PREFIX, BIDS_SUBJECT_PREFIX


def dataset_option(func):
    """Define dataset options for the CLI.

    It is separated from global_options to allow for a different ordering when printing
    the `--help`.
    """
    # The dataset argument is deprecated, but we keep it for backward compatibility.
    func = click.argument(
        "dataset_argument",
        required=False,
        type=click.Path(file_okay=False, path_type=Path, resolve_path=True),
        is_eager=True,
    )(func)
    return click.option(
        "--dataset",
        "dpath_root",
        type=click.Path(file_okay=False, path_type=Path, resolve_path=True),
        required=False,
        default=Path().cwd(),
        show_default=(False if os.environ.get("READTHEDOCS") else True),
        help=(
            "Path to the root of the dataset (default is current working directory)."
        ),
    )(func)


def dep_params(**params):
    """Verify either the dataset option or argument is provided, but not both.

    Raise and exit if both are provided or none are provided.
    """
    _dep_dpath_root = params.pop("dataset_argument")

    if _dep_dpath_root:
        logger.warning(
            (
                "Giving the dataset path without --dataset is deprecated and will "
                "cause an error in a future version."
            ),
        )
    params["dpath_root"] = _dep_dpath_root or params.get("dpath_root")

    return params


def global_options(func):
    """Define global options (no layout) for the CLI."""
    func = click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Verbose mode (Show DEBUG messages).",
    )(func)
    func = click.option(
        "--dry-run",
        is_flag=True,
        help="Print commands but do not execute them.",
    )(func)
    return func


def layout_option(func):
    """Define layout option for the CLI."""
    func = click.option(
        "--layout",
        "fpath_layout",
        type=click.Path(exists=True, path_type=Path, resolve_path=True, dir_okay=False),
        help=(
            "Path to a custom layout specification file,"
            " to be used instead of the default layout."
        ),
    )(func)
    return func


def pipeline_options(func):
    """Define pipeline options for the CLI."""
    func = click.option(
        "--session-id",
        type=str,
        help=f"Session ID (with or without the {BIDS_SESSION_PREFIX} prefix).",
    )(func)
    func = click.option(
        "--participant-id",
        type=str,
        help=f"Participant ID (with or without the {BIDS_SUBJECT_PREFIX} prefix).",
    )(func)
    func = click.option(
        "--pipeline-step",
        type=str,
        help=(
            "Pipeline step, as specified in the pipeline config file "
            "(default: first step)."
        ),
    )(func)
    func = click.option(
        "--pipeline-version",
        type=str,
        help=(
            "Pipeline version, as specified in the pipeline config file "
            "(default: latest out of the installed versions)."
        ),
    )(func)
    func = click.option(
        "--pipeline",
        "pipeline_name",
        type=str,
        required=True,
        help="Pipeline name, as specified in the config file.",
    )(func)
    return func


def runners_options(func):
    """Define options for the pipeline runner commands."""
    func = click.option(
        "--write-list",
        type=click.Path(path_type=Path, resolve_path=True, dir_okay=False),
        help=(
            "Path to a participant-session TSV file to be written. If this is "
            "provided, the pipeline will not be run: instead, a list of "
            "participant and session IDs will be written to this file."
        ),
    )(func)
    func = click.option(
        "--hpc",
        help=(
            "Submit HPC jobs instead of running the pipeline directly. "
            "The value should be the HPC cluster type. Currently, "
            "'slurm' and 'sge' have built-in support, but it is possible to add "
            "other cluster types supported by PySQA (https://pysqa.readthedocs.io/)."
        ),
    )(func)
    func = click.option(
        "--keep-workdir",
        is_flag=True,
        help=(
            "Keep pipeline working directory upon success "
            "(default: working directory deleted unless a run failed)"
        ),
    )(func)
    func = click.option(
        "--simulate",
        is_flag=True,
        help="Simulate the pipeline run without executing the generated command-line.",
    )(func)
    func = pipeline_options(func)
    return func


def assume_yes_option(func):
    """Define assume-yes option for the CLI."""
    func = click.option(
        "--assume-yes",
        "--yes",
        "-y",
        is_flag=True,
        help="Assume yes to all questions.",
    )(func)
    return func
