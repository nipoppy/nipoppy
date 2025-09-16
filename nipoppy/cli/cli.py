"""Nipoppy CLI."""

import subprocess
from pathlib import Path

import rich_click as click

try:
    from trogon import tui
except ImportError:
    # Fallback no-op decorator if Trogon isn't installed
    def tui(*args, **kwargs):
        """No-op decorator for Trogon."""

        def decorator(f):
            return f

        return decorator


from nipoppy._version import __version__
from nipoppy.cli import OrderedAliasedGroup, exception_handler
from nipoppy.cli.options import (
    dataset_option,
    dep_params,
    global_options,
    layout_option,
    pipeline_options,
    runners_options,
)
from nipoppy.cli.pipeline_catalog import pipeline

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
                "--copy-files",
                "--check-dicoms",
                "--tar",
                "--query",
                "--size",
                "--zenodo-id",
                "--password-file",
                "--assume-yes",
                "--sandbox",
                "--force",
            ],
        },
        {
            "name": "Filtering",
            "options": [
                "--participant-id",
                "--session-id",
                "--use-subcohort",
            ],
        },
        {
            "name": "Parallelization",
            "options": [
                "--hpc",
                "--write-subcohort",
                "--n-jobs",
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


@tui(command="gui", help="Open the Nipoppy terminal GUI.")
@click.group(
    cls=OrderedAliasedGroup,
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


if cli.commands.get("gui"):
    cli.commands["gui"].hidden = True


@cli.command()
@dataset_option
@click.option(
    "--bids-source",
    type=click.Path(exists=True, file_okay=False, path_type=Path, resolve_path=True),
    help="Path to a BIDS dataset to initialize the layout with.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help=(
        "Create a nipoppy dataset even if there are already files present"
        " (may clobber existing files)."
    ),
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
@layout_option
def init(**params):
    """Initialize a new dataset."""
    from nipoppy.workflows.dataset_init import InitWorkflow

    params = dep_params(**params)
    with exception_handler(InitWorkflow(**params)) as workflow:
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
    "--force",
    "--regenerate",
    "-f",
    is_flag=True,
    help=(
        "Regenerate the curation status file even if it already exists"
        " (default: only append rows for new records)"
    ),
)
@global_options
@layout_option
def track_curation(**params):
    """Create or update a dataset's curation status file."""
    from nipoppy.workflows.track_curation import TrackCurationWorkflow

    params = dep_params(**params)
    with exception_handler(TrackCurationWorkflow(**params)) as workflow:
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
@layout_option
def reorg(**params):
    """(Re)organize raw (DICOM) files.

    From ``<NIPOPPY_PROJECT_ROOT>/sourcedata/imaging/pre_reorg`` to
    ``<NIPOPPY_PROJECT_ROOT>/sourcedata/imaging/post_reorg``
    """
    from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow

    params = dep_params(**params)
    with exception_handler(DicomReorgWorkflow(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
@global_options
@layout_option
def bidsify(**params):
    """Run a BIDS conversion pipeline."""
    from nipoppy.workflows.bids_conversion import BIDSificationRunner

    params = dep_params(**params)
    with exception_handler(BIDSificationRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
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
@layout_option
def process(**params):
    """Run a processing pipeline."""
    from nipoppy.workflows.processing_runner import ProcessingRunner

    params = dep_params(**params)
    with exception_handler(ProcessingRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@pipeline_options
@click.option(
    "--n-jobs",
    type=int,
    default=1,
    show_default=True,
    help=("Number of parallel workers to use."),
)
@global_options
@layout_option
def track_processing(**params):
    """Track the processing status of a pipeline."""
    from nipoppy.workflows.tracker import PipelineTracker

    params = dep_params(**params)
    with exception_handler(PipelineTracker(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@runners_options
@global_options
@layout_option
def extract(**params):
    """Extract imaging-derived phenotypes (IDPs) from processed data."""
    from nipoppy.workflows.extractor import ExtractionRunner

    params = dep_params(**params)
    with exception_handler(ExtractionRunner(**params)) as workflow:
        workflow.run()


@cli.command()
@dataset_option
@global_options
@layout_option
def status(**params):
    """Print a summary of the dataset."""
    from nipoppy.workflows.dataset_status import StatusWorkflow

    params = dep_params(**params)
    with exception_handler(StatusWorkflow(**params)) as workflow:
        workflow.run()


######################################
# Command groups from external files #
######################################
cli.add_command(pipeline)


#############
# TUI alias #
#############
def tui_launch():  # pragma: no cover
    """Launch the Nipoppy TUI."""
    subprocess.run(["nipoppy", "gui"])
