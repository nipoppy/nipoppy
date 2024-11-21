import sys
from pathlib import Path

import click


def global_options(func):
    func = click.option(
        "--dataset", "dpath_root", type=click.Path(exists=False), default=Path().cwd()
    )(func)
    func = click.option("--dry-run", "-n", is_flag=True)(func)
    func = click.option("--layout", "fpath_layout", type=click.Path(exists=True))(func)
    func = click.option("--verbose", "-v", count=True)(func)
    return func


def pipeline_options(func):
    func = click.option("--pipeline", "pipeline_name", type=str)(func)
    func = click.option("--pipeline-version", type=str)(func)
    func = click.option("--pipeline-step", type=str)(func)
    func = click.option("--participant-id", type=str)(func)
    func = click.option("--session-id", type=str)(func)
    return func


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    pass


@cli.command()
@global_options
@click.option("--bids-source", type=click.Path(exists=True))
def init(**params):
    from nipoppy.workflows.dataset_init import InitWorkflow

    workflow = InitWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@click.option("--empty", is_flag=True)
@click.option("--regenerate", "--force", "-f", type=bool)
def doughnut(**params):
    from nipoppy.workflows.doughnut import DoughnutWorkflow

    workflow = DoughnutWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@click.option("--copy-files", type=bool)
@click.option("--check-dicoms", type=bool)
def reorg(**params):
    from nipoppy.workflows.dicom_reorg import DicomReorgWorkflow

    workflow = DicomReorgWorkflow(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@pipeline_options
@click.option("--simulate", type=bool)
def bidsify(**params):
    from nipoppy.workflows.bids_conversion import BidsConversionRunner

    workflow = BidsConversionRunner(**params)
    workflow.run()
    sys.exit(workflow.return_code)


cli.add_command(bidsify, name="convert")  # Alias


@cli.command()
@global_options
@pipeline_options
@click.option("--keep-workdir", type=bool)
@click.option("--simulate", type=bool)
def run(**params):
    from nipoppy.workflows.runner import PipelineRunner

    workflow = PipelineRunner(**params)
    workflow.run()
    sys.exit(workflow.return_code)


@cli.command()
@global_options
@pipeline_options
def track(**params):
    from nipoppy.workflows.tracker import PipelineTracker

    workflow = PipelineTracker(**params)
    workflow.run()
    sys.exit(workflow.return_code)


if __name__ == "__main__":
    cli()
