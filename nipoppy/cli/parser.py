"""Parsers for the CLI."""
import logging
from argparse import ArgumentParser, HelpFormatter, _SubParsersAction
from pathlib import Path

DEFAULT_VERBOSITY = "3"  # debug
VERBOSITY_TO_LOG_LEVEL_MAP = {
    "0": logging.ERROR,
    "1": logging.WARNING,
    "2": logging.INFO,
    "3": logging.DEBUG,
}


def add_arg_dataset_root(parser: ArgumentParser) -> ArgumentParser:
    """Add common arguments (e.g., dataset root) to the parser."""
    parser.add_argument(
        "--dataset-root",
        "--dataset_root",
        type=Path,
        required=True,
    )
    return parser


def add_arg_help(parser: ArgumentParser) -> ArgumentParser:
    """Add a help argument."""
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )
    return parser


def add_arg_verbosity(parser: ArgumentParser) -> ArgumentParser:
    """Add generic arguments (e.g., verbosity) to the parser."""

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
    subparsers: _SubParsersAction, formatter_class: type[HelpFormatter] = HelpFormatter
) -> ArgumentParser:
    """Add subparser for init command."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new dataset.",
        formatter_class=formatter_class,
        add_help=False,
    )
    parser = add_arg_dataset_root(parser)
    parser = add_arg_verbosity(parser)
    parser = add_arg_help(parser)


def get_global_parser(
    formatter_class: type[HelpFormatter] = HelpFormatter,
) -> ArgumentParser:
    """Get the global parser."""
    parser = ArgumentParser(
        prog="nipoppy",
        description="Organize and process neuroimaging-clinical datasets.",
        formatter_class=formatter_class,
        add_help=False,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Choose a subcommand",
        required=True,
    )

    add_subparser_init(subparsers, formatter_class=formatter_class)

    parser = add_arg_help(parser)

    return parser
