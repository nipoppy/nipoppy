"""Nipoppy CLI."""

import sys
from pathlib import Path

import click

from nipoppy._version import __version__
from nipoppy.env import BIDS_SESSION_PREFIX, BIDS_SUBJECT_PREFIX, DEFAULT_VERBOSITY


def global_options(func):
    """Define global options for the CLI."""
    func = click.option(
        "--dataset",
        "dpath_root",
        type=click.Path(),
        default=Path().cwd(),
        help="Path to the root of the dataset.",
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
        type=click.Path(exists=True),
        help=(
            "Path to a custom layout specification file,"
            " to be used instead of the default layout."
        ),
    )(func)
    func = click.option(
        "--verbose",
        "-v",
        count=True,
        default=DEFAULT_VERBOSITY,
        help="Verbosity level, Verbosity level, from 0 (least verbose) "
        "to 3 (most verbose). Default: {DEFAULT_VERBOSITY}.",
    )(func)
    return func


def pipeline_options(func):
    """Define pipeline options for the CLI."""
    func = click.option(
        "--pipeline",
        "pipeline_name",
        type=str,
        help="Pipeline name, as specified in the config file.",
    )(func)
    func = click.option(
        "--pipeline-version",
        type=str,
        help="Pipeline version, as specified in the config file.",
    )(func)
    func = click.option(
        "--pipeline-step",
        type=str,
        help="Pipeline step, as specified in the config file (default: first step).",
    )(func)
    func = click.option(
        "--participant-id",
        type=str,
        help=f"Participant ID (with or without the {BIDS_SUBJECT_PREFIX} prefix).",
    )(func)
    func = click.option(
        "--session-id",
        type=str,
        help=f"Session ID (with or without the {BIDS_SESSION_PREFIX} prefix).",
    )(func)
    return func


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__)
def cli():
    """Nipoppy base CLI."""
    pass


@cli.command()
@global_options
@click.option(
    "--bids-source",
    type=click.Path(exists=True),
    help=("Path to a BIDS dataset to initialize the layout with."),
)
def init(**params):
    """Command: nipoppy init."""
    from nipoppy.workflows.dataset_init import InitWorkflow

    workflow = InitWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
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
def doughnut(**params):
    """Command: nipoppy doughnut."""
    from nipoppy.workflows.doughnut import DoughnutWorkflow

    workflow = DoughnutWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
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
def reorg(**params):
    """Command: nipoppy reorg."""
    from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow

    workflow = DicomReorgWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@pipeline_options
@click.option(
    "--simulate",
    is_flag=True,
    help="Simulate the pipeline run without executing the generated command-line.",
)
def bidsify(**params):
    """Command: nipoppy bidsify."""
    from nipoppy.workflows.bids_conversion import BidsConversionRunner

    workflow = BidsConversionRunner(**params)
    workflow.run()
    sys.exit(workflow.return_code)


cli.add_command(bidsify, name="convert")  # Alias


@cli.command()
@global_options
@pipeline_options
@click.option(
    "--keep-workdir",
    is_flag=True,
    help=(
        "Keep pipeline working directory upon success "
        "(default: working directory deleted unless a run failed)"
    ),
)
@click.option(
    "--simulate",
    is_flag=True,
    help="Simulate the pipeline run without executing the generated command-line.",
)
def run(**params):
    """Command: nipoppy run."""
    from nipoppy.workflows.runner import PipelineRunner

    workflow = PipelineRunner(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@pipeline_options
def track(**params):
    """Command: nipoppy track."""
    from nipoppy.workflows.tracker import PipelineTracker

    workflow = PipelineTracker(**params)
    workflow.run()
    sys.exit(workflow.return_code)


if __name__ == "__main__":
    cli()
