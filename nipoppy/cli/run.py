"""CLI."""
import sys
from typing import Sequence

from rich_argparse import RichHelpFormatter

from nipoppy.cli.parser import get_global_parser


def cli(argv: Sequence[str] = None) -> None:
    """CLI entrypoint."""
    if argv is None:
        argv = sys.argv
    parser = get_global_parser(formatter_class=RichHelpFormatter)
    args, unknown = parser.parse_known_args(argv[1:])
    if len(unknown) > 0:
        parser.error(f"Invalid arguments: {unknown}")
