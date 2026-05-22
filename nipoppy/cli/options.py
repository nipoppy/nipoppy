"""Define shared Click options for the Nipoppy CLI."""

import os
from pathlib import Path
from typing import Any

import rich_click as click
from dotenv import load_dotenv

from nipoppy.env import BIDS_SESSION_PREFIX, BIDS_SUBJECT_PREFIX
from nipoppy.logger import get_logger
from nipoppy.utils.utils import is_nipoppy_project, process_template_str

logger = get_logger()

# from highest to lowest priority
DEFAULT_DOTENV_PATHS_LIST = [
    "[[NIPOPPY_DPATH_ROOT]]/.env",
    "~/.nipoppy/.env",
    "/etc/nipoppy/.env",
]

DOTENV_PATHS_VAR = "NIPOPPY_ENV_PATHS"
DEFAULT_DOTENV_PATHS = os.pathsep.join(DEFAULT_DOTENV_PATHS_LIST)


def _load_env_files(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    """Load environment variable files specified by NIPOPPY_ENV_PATHS.

    This callback function should be used with a hidden and eager Click flag option.
    """
    if value is True:
        ctx.fail(
            f"The {param.opts[0]} option exists for internal reasons and should never be used on the command-line."  # noqa: E501
        )

    # Nipoppy root directory
    dpath_root = ctx.params.get("dataset_argument") or ctx.params.get("dpath_root")
    if dpath_root is not None:
        dpath_root = is_nipoppy_project(dpath_root) or dpath_root
    else:
        dpath_root = Path.cwd()

    fpaths_dotenv_str = os.environ.get(DOTENV_PATHS_VAR, DEFAULT_DOTENV_PATHS)
    fpaths_dotenv_str = process_template_str(fpaths_dotenv_str, dpath_root=dpath_root)

    for fpath_dotenv in fpaths_dotenv_str.split(os.pathsep):
        fpath_dotenv = Path(fpath_dotenv).expanduser()
        if fpath_dotenv.is_file():
            # the logger only logs at INFO or higher at this point
            logger.info(f"Loading environment variables from {fpath_dotenv}")

            # load_dotenv logs warnings instead of raising exceptions
            # so no need to catch them
            load_dotenv(fpath_dotenv, override=False)

    return value


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
        default=Path.cwd(),
        show_default=(False if os.environ.get("READTHEDOCS") else True),
        help="Path to the root of the dataset. Default: current working directory or the closest parent directory that contains a .nipoppy directory.",  # noqa: E501
        is_eager=True,
    )(func)


def dep_params(**params):
    """Handle deprecated parameters."""
    # Verify either the dataset option or argument is provided, but not both.
    if "dpath_root" in params and (_dep_dpath_root := params.pop("dataset_argument")):
        logger.warning(
            (
                "Giving the dataset path without --dataset is deprecated and will "
                "cause an error in a future version."
            ),
        )
        params["dpath_root"] = _dep_dpath_root or params.get("dpath_root")

    # --write-list is deprecated by --write-subcohort
    if "write_subcohort" in params and (
        _dep_write_subcohort := params.pop("write_list")
    ):
        logger.warning(
            "The --write-list option is deprecated and will be removed in a future "
            "version. Use --write-subcohort instead."
        )
        params["write_subcohort"] = _dep_write_subcohort

    return params


def global_options(func):
    """Define global options for the CLI."""
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
    func = click.option(
        "--_env",
        help="This option exists solely to trigger the loading of environment variable files and should never be used directly.",  # noqa: E501
        is_flag=True,
        hidden=True,
        expose_value=False,
        is_eager=True,
        callback=_load_env_files,
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
        envvar="NIPOPPY_LAYOUT",
        show_envvar=True,
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
        "--write-subcohort",
        type=click.Path(path_type=Path, resolve_path=True, dir_okay=False),
        help=(
            "Path to a participant-session TSV file to be written. If this is "
            "provided, the pipeline will not be run: instead, a list of "
            "participant and session IDs will be written to this file."
        ),
    )(func)
    # alias: to be deprecated
    func = click.option(
        "--write-list",
        type=click.Path(path_type=Path, resolve_path=True, dir_okay=False),
        hidden=True,
    )(func)
    func = click.option(
        "--use-subcohort",
        type=click.Path(path_type=Path, exists=True, resolve_path=True, dir_okay=False),
        help=(
            "Path to a TSV file containing participant-session pairs to be used. "
            "This file should have the same format as the file generated by "
            "--write-subcohort: it should have no headers, the first column should "
            f"contain participant IDs (without the {BIDS_SUBJECT_PREFIX} prefix), and "
            "the second column should contain session IDs (without the "
            f"{BIDS_SESSION_PREFIX} prefix)."
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


def password_file_option(required: bool):
    """
    Define password file option for the CLI.

    Note: This is a decorator factory that returns a decorator.
    """

    def decorator(func):
        return click.option(
            "--password-file",
            type=click.Path(
                exists=True, path_type=Path, resolve_path=True, dir_okay=False
            ),
            required=required,
            help="Path to file containing Zenodo access token (and nothing else)",
        )(func)

    return decorator
