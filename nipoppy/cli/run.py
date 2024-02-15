"""Command-line interface."""
import sys
from typing import Sequence

from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import COMMAND_INIT, get_global_parser
from nipoppy.logger import add_logfile, get_logger
from nipoppy.workflows.dataset_init import DatasetInitWorkflow


def cli(argv: Sequence[str] = None) -> None:
    """Entrypoint to the command-line interface."""
    if argv is None:
        argv = sys.argv
    parser = get_global_parser(formatter_class=RichHelpFormatter)
    args = parser.parse_args(argv[1:])

    # common arguments
    command = args.command
    logger = get_logger(level=args.verbosity)
    dry_run = args.dry_run

    # to pass to all workflows
    workflow_kwargs = dict(logger=logger, dry_run=dry_run)

    try:
        dpath_root = args.dataset_root

        if command == COMMAND_INIT:
            workflow = DatasetInitWorkflow(
                dpath_root=dpath_root,
                **workflow_kwargs,
            )
        else:
            raise ValueError(f"Unsupported command: {command}")

        # cannot log to file in init since the dataset doesn't exist yet
        if command != COMMAND_INIT:
            add_logfile(logger, workflow.generate_fpath_log())

        # run the workflow
        workflow.run()

        return workflow

    except Exception:
        logger.exception("Error when creating/running a workflow")
        sys.exit(1)
