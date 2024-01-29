"""Command-line interface."""
import sys
from typing import Sequence

from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import get_global_parser
from nipoppy.logger import get_logger


def cli(argv: Sequence[str] = None) -> None:
    """Entrypoint to the command-line interface."""
    if argv is None:
        argv = sys.argv
    parser = get_global_parser(formatter_class=RichHelpFormatter)
    args, unknown = parser.parse_known_args(argv[1:])

    logger = get_logger(level=args.verbosity)

    if len(unknown) > 0:
        parser.error(f"Invalid arguments: {unknown}")

    logger.info(f"Parsed arguments: {args}")
