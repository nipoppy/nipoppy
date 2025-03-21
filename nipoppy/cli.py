"""Nipoppy CLI."""

import sys
from contextlib import contextmanager
from pathlib import Path

import rich_click as click

from nipoppy._version import __version__
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    PROGRAM_NAME,
    ReturnCode,
)
from nipoppy.logger import get_logger

logger = get_logger(
    name=f"{PROGRAM_NAME}.{__name__}",
)


@contextmanager
def handle_exception(workflow):
    """Handle exceptions raised during workflow execution."""
    try:
        yield workflow
    except Exception:
        workflow.logger.exception("Error while running nipoppy")
        if workflow.return_code == ReturnCode.SUCCESS:
            workflow.return_code = ReturnCode.UNKOWN_FAILURE
    finally:
        sys.exit(workflow.return_code)


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
        show_default=True,
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
                "The dataset argument is deprecated."
                "Use the --dataset option in the future."
            ),
        )
    params["dpath_root"] = _dep_dpath_root or params.get("dpath_root")

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
        "-n",
        is_flag=True,
        help="Print commands but do not execute them.",
    )(func)
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
        help="Pipeline step, as specified in the config file (default: first step).",
    )(func)
    func = click.option(
        "--pipeline-version",
        type=str,
        help="Pipeline version, as specified in the config file.",
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
        "--simulate",
        is_flag=True,
        help="Simulate the pipeline run without executing the generated command-line.",
    )(func)
    func = click.option(
        "--write-list",
        type=click.Path(path_type=Path, resolve_path=True, dir_okay=False),
        help=(
            "Path to a participant-session TSV file to be written. If this is "
            "provided, the pipeline will not be run: instead, a list of "
            "participant and session IDs will be written to this file."
        ),
    )(func)
    func = pipeline_options(func)
    return func


class OrderedGroup(click.RichGroup):
    """Group that lists commands in the order they were added."""

    def list_commands(self, ctx):
        """List commands in the order they were added."""
        return list(self.commands.keys())


click.rich_click.OPTION_GROUPS = {
    "nipoppy *": [
        {
            "name": "Command-specific",
            "options": [
                "--dataset",
                "--pipeline",
                "--pipeline-version",
                "--pipeline-step",
                "--bids-source",
                "--mode",
                "--empty",
                "--regenerate",
                "--copy-files",
                "--check-dicoms",
                "--tar",
            ],
        },
        {
            "name": "Filtering",
            "options": [
                "--participant-id",
                "--session-id",
            ],
        },
        {
            "name": "Parallelization",
            "options": [
                "--hpc",
                "--write-list",
            ],
        },
        {
            "name": "Troubleshooting",
            "options": [
                "--verbose",
                "--dry-run",
                "--simulate",
                "--keep-workdir",
            ],
        },
        {
            "name": "Miscellaneous",
            "options": [
                "--layout",
                "--help",
            ],
        },
    ]
}


@click.group(
    cls=OrderedGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=(
        "Run 'nipoppy COMMAND --help' for more information on a subcommand.\n\n"
        "Or visit the documentation at https://nipoppy.readthedocs.io"
    ),
)
@click.version_option(version=__version__)
def cli():
    """Organize and process neuroimaging-clinical datasets."""
    pass


@cli.command()
@dataset_option
@click.option(
    "--bids-source",
    type=click.Path(exists=True, file_okay=False, path_type=Path, resolve_path=True),
    help=("Path to a BIDS dataset to initialize the layout with."),
)
@click.option(
    "--mode",
    type=click.Choice(["copy", "move", "symlink"]),
    default="symlink",
    show_default=True,
    help=(
        "If using a BIDS source, specify whether to copy, move, or symlink the files."
    ),
)
@global_options
def init(**params):
    """Initialize a new dataset."""
    from nipoppy.workflows.dataset_init import InitWorkflow

    params = dep_params(**params)
    with handle_exception(InitWorkflow(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@click.option(
    "--empty",
    is_flag=True,
    help=(
        "Set all statuses to False in newly added records"
        " (regardless of what is on disk). May be useful to reduce runtime."
    ),
)
@click.option(
    "--regenerate",
    "--force",
    "-f",
    is_flag=True,
    help=(
        "Regenerate the doughnut file even if it already exists"
        " (default: only append rows for new records)"
    ),
)
@global_options
def doughnut(**params):
    """Create or update a dataset's doughnut file."""
    from nipoppy.workflows.doughnut import DoughnutWorkflow

    params = dep_params(**params)
    with handle_exception(DoughnutWorkflow(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@click.option(
    "--copy-files",
    is_flag=True,
    help="Copy files when reorganizing (default: create symlinks).",
)
@click.option(
    "--check-dicoms",
    is_flag=True,
    help=(
        "Read DICOM file headers when reorganizing and check if they have the "
        '"DERIVED" image type (which can be problematic for some BIDS '
        "converters). The paths to the derived DICOMs will be written to the log."
    ),
)
@global_options
def reorg(**params):
    """(Re)organize raw (DICOM) files.

    From ``<DATASET_ROOT>/sourcedata/imaging/pre_reorg`` to
    ``<DATASET_ROOT>/sourcedata/imaging/post_reorg``
    """
    from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow

    params = dep_params(**params)
    with handle_exception(DicomReorgWorkflow(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
@global_options
def bidsify(**params):
    """Run a BIDS conversion pipeline."""
    from nipoppy.workflows.bids_conversion import BidsConversionRunner

    params = dep_params(**params)
    with handle_exception(BidsConversionRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
@click.option(
    "--keep-workdir",
    is_flag=True,
    help=(
        "Keep pipeline working directory upon success "
        "(default: working directory deleted unless a run failed)"
    ),
)
@click.option(
    "--tar",
    is_flag=True,
    help=(
        "Archive participant-session-level results into a tarball upon "
        "successful completion. The path to be archived should be specified "
        "in the tracker configuration file."
    ),
)
@global_options
def run(**params):
    """Run a processing pipeline."""
    from nipoppy.workflows.runner import PipelineRunner

    params = dep_params(**params)
    with handle_exception(PipelineRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@pipeline_options
@global_options
def track(**params):
    """Track the processing status of a pipeline."""
    from nipoppy.workflows.tracker import PipelineTracker

    params = dep_params(**params)
    with handle_exception(PipelineTracker(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
@global_options
def extract(**params):
    """Extract imaging-derived phenotypes (IDPs) from processed data."""
    from nipoppy.workflows.extractor import ExtractionRunner

    params = dep_params(**params)
    with handle_exception(ExtractionRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@global_options
def status(**params):
    """Workflow for status command."""
    from nipoppy.workflows.dataset_status import StatusWorkflow

    params = dep_params(**params)
    with handle_exception(StatusWorkflow(**params)) as workflow:
        workflow.run()
