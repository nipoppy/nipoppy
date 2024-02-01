"""Parsers for the CLI."""
import logging
from argparse import ArgumentParser, HelpFormatter, _ActionsContainer, _SubParsersAction
from pathlib import Path

PROGRAM_NAME = "nipoppy"
COMMAND_INIT = "init"

DEFAULT_VERBOSITY = "3"  # debug
VERBOSITY_TO_LOG_LEVEL_MAP = {
    "0": logging.ERROR,
    "1": logging.WARNING,
    "2": logging.INFO,
    "3": logging.DEBUG,
}


def add_arg_dataset_root(parser: _ActionsContainer) -> _ActionsContainer:
    """Add a --dataset-root argument to the parser."""
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="Path to the root of the dataset.",
    )
    return parser


def add_arg_dry_run(parser: _ActionsContainer) -> _ActionsContainer:
    """Add a --dry-run argument to the parser."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands but do not execute them.",
    )
    return parser


def add_arg_help(parser: _ActionsContainer) -> _ActionsContainer:
    """Add a --help argument to the parser."""
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help message and exit.",
    )
    return parser


def add_arg_verbosity(parser: _ActionsContainer) -> _ActionsContainer:
    """Add a --verbosity argument to the parser."""

    def _verbosity_to_log_level(verbosity: str):
        try:
            return VERBOSITY_TO_LOG_LEVEL_MAP[verbosity]
        except KeyError:
            parser.error(
                f"Invalid verbosity level: {verbosity}."
                f" Valid levels are {list(VERBOSITY_TO_LOG_LEVEL_MAP.keys())}."
            )

    parser.add_argument(
        "--verbosity",
        type=_verbosity_to_log_level,
        default=DEFAULT_VERBOSITY,
        help=(
            "Verbosity level, from 0 (least verbose) to 3 (most verbose)."
            f" Default: {DEFAULT_VERBOSITY}."
        ),
    )
    return parser


def add_subparser_init(
    subparsers: _SubParsersAction,
    formatter_class: type[HelpFormatter] = HelpFormatter,
) -> ArgumentParser:
    """Add subparser for init command."""
    parser = subparsers.add_parser(
        COMMAND_INIT,
        help="Initialize a new dataset.",
        formatter_class=formatter_class,
        add_help=False,
    )
    parser = add_arg_dataset_root(parser)
    return parser


def get_global_parser(
    formatter_class: type[HelpFormatter] = HelpFormatter,
) -> ArgumentParser:
    """Get the global parser."""
    global_parser = ArgumentParser(
        prog=PROGRAM_NAME,
        description="Organize and process neuroimaging-clinical datasets.",
        formatter_class=formatter_class,
        add_help=False,
    )

    # subcommand parsers
    subparsers = global_parser.add_subparsers(
        dest="command",
        help="Choose a subcommand.",
        required=True,
    )
    add_subparser_init(subparsers, formatter_class=formatter_class)

    # add common/global options to main and subcommand parsers
    for parser in [global_parser] + list(subparsers.choices.values()):
        common_arg_group = parser.add_argument_group("Global options")
        add_arg_verbosity(common_arg_group)
        add_arg_dry_run(common_arg_group)
        add_arg_help(common_arg_group)

    return global_parser
