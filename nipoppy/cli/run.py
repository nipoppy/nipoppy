"""Command-line interface."""

import importlib
import logging
import sys
from typing import Sequence

from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import (
    COMMAND_BIDS_CONVERSION,
    COMMAND_DICOM_REORG,
    COMMAND_DOUGHNUT,
    COMMAND_INIT,
    COMMAND_PIPELINE_EXTRACT,
    COMMAND_PIPELINE_RUN,
    COMMAND_PIPELINE_TRACK,
    COMMAND_STATUS,
    PROGRAM_NAME,
    VERBOSITY_TO_LOG_LEVEL_MAP,
    get_global_parser,
)
from nipoppy.logger import add_logfile, capture_warnings, get_logger

COMMAND_TO_WORKFLOW_MAP = {
    COMMAND_INIT: ("nipoppy.workflows.dataset_init", "InitWorkflow"),
    COMMAND_STATUS: ("nipoppy.workflows.dataset_status", "StatusWorkflow"),
    COMMAND_DOUGHNUT: ("nipoppy.workflows.doughnut", "DoughnutWorkflow"),
    COMMAND_DICOM_REORG: ("nipoppy.workflows.dicom_reorg", "DicomReorgWorkflow"),
    COMMAND_BIDS_CONVERSION: (
        "nipoppy.workflows.bids_conversion",
        "BidsConversionRunner",
    ),
    COMMAND_PIPELINE_RUN: ("nipoppy.workflows.runner", "PipelineRunner"),
    COMMAND_PIPELINE_TRACK: ("nipoppy.workflows.tracker", "PipelineTracker"),
    COMMAND_PIPELINE_EXTRACT: ("nipoppy.workflows.extractor", "ExtractionRunner"),
}


def cli(argv: Sequence[str] = None) -> None:
    """Entrypoint to the command-line interface."""
    if argv is None:
        argv = sys.argv
    parser = get_global_parser(formatter_class=RichHelpFormatter)
    parsed_args = vars(parser.parse_args(argv[1:]))

    # create logger
    command = parsed_args.pop("command")
    logger = get_logger(
        name=f"{PROGRAM_NAME}.{command}",
        level=VERBOSITY_TO_LOG_LEVEL_MAP[parsed_args.pop("verbosity")],
    )

    dpath_root = parsed_args.pop("dataset_root")

    try:
        try:
            module, workflow_class = COMMAND_TO_WORKFLOW_MAP[command]
        except KeyError:
            raise ValueError(f"Unsupported command: {command}")

        # create the workflow dynamically
        workflow = getattr(importlib.import_module(module), workflow_class)(
            dpath_root=dpath_root,
            logger=logger,
            **parsed_args,
        )

        # cannot log to file in init since the dataset doesn't exist yet
        if command not in [COMMAND_INIT, COMMAND_STATUS]:
            add_logfile(logger, workflow.generate_fpath_log())

        # capture warnings
        logging.captureWarnings(True)
        capture_warnings(workflow.logger)

        # run the workflow
        workflow.run()

        # exit with the workflow's return code
        sys.exit(workflow.return_code)

    except Exception:
        logger.exception("Error when creating/running a workflow")
        sys.exit(1)
