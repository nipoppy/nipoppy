"""Define CLI for the Nipoppy pipeline catalog."""

from pathlib import Path

import rich_click as click

from nipoppy.cli import OrderedAliasedGroup, handle_exception
from nipoppy.cli.options import (
    assume_yes_option,
    dataset_option,
    dep_params,
    global_options,
    layout_option,
)
from nipoppy.env import PipelineTypeEnum


@click.group(
    cls=OrderedAliasedGroup, context_settings={"help_option_names": ["-h", "--help"]}
)
def pipeline():
    """Pipeline store operations."""
    pass


def zenodo_options(func):
    """Define Zenodo options for the CLI."""
    func = click.option(
        "--sandbox",
        "sandbox",
        is_flag=True,
        help="Use the Zenodo sandbox API for tests.",
    )(func)
    return func


@pipeline.command("search")
@click.argument("query", type=str, default="")
@click.option(
    "--size",
    "-s",
    "-n",
    type=click.IntRange(min=1),
    help="Number of items to show",
    default=10,
    show_default=True,
)
@zenodo_options
@global_options
def pipeline_search(**params):
    """Search for available pipelines on Zenodo."""
    from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow

    with handle_exception(PipelineSearchWorkflow(**params)) as workflow:
        workflow.run()


@pipeline.command("create")
@click.argument(
    "pipeline_dir",
    type=click.Path(exists=False, path_type=Path, resolve_path=True),
)
@click.option(
    "--type",
    "-t",
    "type_",
    type=click.Choice(
        [
            PipelineTypeEnum.BIDSIFICATION,
            PipelineTypeEnum.PROCESSING,
            PipelineTypeEnum.EXTRACTION,
        ],
        case_sensitive=False,
    ),
    required=True,
    help=(
        "Pipeline type. This is used to create the correct pipeline config directory."
    ),
)
@click.option(
    "--source-descriptor",
    type=click.Path(exists=True, path_type=Path, resolve_path=True, dir_okay=False),
    help=(
        "Path to an existing Boutiques descriptor file. This is used to create the "
        "pipeline config directory."
    ),
)
@global_options
def pipeline_create(**params):
    """Create a template pipeline config directory."""
    from nipoppy.workflows.pipeline_store.create import PipelineCreateWorkflow

    with handle_exception(PipelineCreateWorkflow(**params)) as workflow:
        workflow.run()


@pipeline.command("install")
@click.argument(
    "source",
    type=str,
)
@zenodo_options
@dataset_option
@click.option(
    "--force",
    "-f",
    "--overwrite",
    is_flag=True,
    help="Overwrite existing pipeline directory if it exists.",
)
@global_options
@layout_option
@assume_yes_option
def pipeline_install(**params):
    """
    Install a new pipeline into a dataset.

    The source of the pipeline can be a local directory or a Zenodo ID.
    """
    from nipoppy.workflows.pipeline_store.install import PipelineInstallWorkflow

    params = dep_params(**params)
    with handle_exception(PipelineInstallWorkflow(**params)) as workflow:
        workflow.run()


@pipeline.command("list")
@dataset_option
@global_options
@layout_option
def pipeline_list(**params):
    """List installed pipelines for a dataset."""
    from nipoppy.workflows.pipeline_store.list import PipelineListWorkflow

    params = dep_params(**params)
    with handle_exception(PipelineListWorkflow(**params)) as workflow:
        workflow.run()


@pipeline.command("validate")
@click.argument(
    "pipeline_dir",
    required=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False, resolve_path=True),
)
@global_options
def pipeline_validate(**params):
    """Validate a pipeline config directory."""
    from nipoppy.workflows.pipeline_store.validate import PipelineValidateWorkflow

    params["dpath_pipeline"] = params.pop("path")
    with handle_exception(PipelineValidateWorkflow(**params)) as workflow:
        workflow.run()


@pipeline.command("upload")
@click.argument(
    "pipeline_dir",
    type=str,
)
@click.option(
    "--zenodo-id",
    "record_id",
    type=str,
    required=False,
    help="To update an existing pipeline, provide the Zenodo ID.",
)
@assume_yes_option
@click.option(
    "--password-file",
    type=click.Path(exists=True, path_type=Path, resolve_path=True, dir_okay=False),
    required=True,
    help="Path to file containing Zenodo access token (and nothing else)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Ignore safeguard warnings and upload anyway. Use with caution.",
)
@zenodo_options
@global_options
def pipeline_upload(**params):
    """Upload a pipeline config directory to Zenodo."""
    from nipoppy.workflows.pipeline_store.upload import PipelineUploadWorkflow

    with handle_exception(PipelineUploadWorkflow(**params)) as workflow:
        workflow.run()
