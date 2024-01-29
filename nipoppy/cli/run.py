"""CLI."""
import sys
from typing import Sequence

from nipoppy.cli.parser import get_global_parser


def cli(argv: Sequence[str] = None) -> None:
    """CLI entrypoint."""
    if argv is None:
        argv = sys.argv
    parser = get_global_parser()
    args, unknown = parser.parse_known_args(argv[1:])
    if len(unknown) > 0:
        parser.error(f"Invalid arguments: {unknown}")
