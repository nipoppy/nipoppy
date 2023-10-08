#!/usr/bin/env python
from functools import partial
from pathlib import Path
from nipoppy.logging import create_logger
from nipoppy.parser import get_base_parser, REQUIRED_ARG
from nipoppy.workflow.runner import ProcpipeRunner
from nipoppy.workflow.proc_pipe.fmriprep.fmriprep_runner import FmriprepRunner
from nipoppy.workflow.proc_pipe.mriqc.mriqc_runner import MriqcRunner

DESCRIPTION = 'Run a processing pipeline for a single subject and session.'
LOGGER_NAME = Path(__file__).stem

RUNNERS = {
    'fmriprep': FmriprepRunner,
    'mriqc': MriqcRunner,
}

def run(global_configs, pipeline_name, subject, session, pipeline_version=None,
        logger=None, log_level=None, aggregate_logs=False, dry_run=False):
    
    if logger is None:
        logger = create_logger(name=LOGGER_NAME)

    if aggregate_logs:
        logger.info('Aggregating logs')
        runner_logger = logger
    else:
        runner_logger = None
    
    try:
        runner_constructor = RUNNERS[pipeline_name]
    except KeyError:
        runner_constructor = partial(
            ProcpipeRunner,
            pipeline_name=pipeline_name,
        )

    runner: ProcpipeRunner = runner_constructor(
        global_configs=global_configs,
        subject=subject,
        session=session,
        pipeline_version=pipeline_version,
        logger=runner_logger,
        log_level=log_level,
        dry_run=dry_run,
    )

    runner.run()

if __name__ == '__main__':

    # get standard args
    parser = get_base_parser(
        description=DESCRIPTION,
        subject=REQUIRED_ARG,
        session=REQUIRED_ARG,
    )

    # add script-specific args
    parser.add_argument(
        '--pipeline',
        '--pipeline-name',
        '--pipeline_name',
        type=str,
        required=True,
        help=(
            f'Name of pipeline to run. Can be one of: {list(RUNNERS.keys())}'
            ' or a custom one defined in the global configs.'
        ),
    )
    parser.add_argument(
        '--pipeline-version',
        '--pipeline_version',
        type=str,
        required=False,
        help=(
            'Version of pipeline to run. If not provided, will'
            ' use the first one listed in the global configs.'
        ),
    )
    # add common optional args
    parser.add_generic_optional_args(logger_name=LOGGER_NAME)

    args = parser.parse_args()

    run(
        global_configs=args.global_configs,
        pipeline_name=args.pipeline,
        pipeline_version=args.pipeline_version,
        subject=args.subject,
        session=args.session,
        dry_run=args.dry_run,
        logger=args.logger,
        log_level=args.log_level,
        aggregate_logs=args.aggregate_logs,
    )
