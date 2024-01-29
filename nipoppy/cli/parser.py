"""Parsers for the CLI."""
import logging
from argparse import ArgumentParser, HelpFormatter

DEFAULT_VERBOSITY = 2  # info
VERBOSITY_TO_LOG_LEVEL_MAP = {
    "0": logging.ERROR,
    "1": logging.WARNING,
    "2": logging.INFO,
    "3": logging.DEBUG,
}


def get_base_parser(
    formatter_class: type[HelpFormatter] = HelpFormatter,
) -> ArgumentParser:
    """Get the base parser.

    Returns
    -------
    ArgumentParser
    """
    parser = ArgumentParser(
        prog="nipoppy",
        description="Organize and process neuroimaging-clinical datasets.",
        formatter_class=formatter_class,
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )
    return parser


def add_generic_arguments(parser: ArgumentParser) -> ArgumentParser:
    """Add generic arguments (e.g., verbosity) to the parser.

    Parameters
    ----------
    parser : ArgumentParser
        Parser to add arguments to.

    Returns
    -------
    ArgumentParser
    """

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


def get_global_parser(
    formatter_class: type[HelpFormatter] = HelpFormatter,
) -> ArgumentParser:
    """Get the global parser.

    Returns
    -------
    ArgumentParser
    """
    parser = get_base_parser(formatter_class=formatter_class)
    parser = add_generic_arguments(parser)
    return parser
