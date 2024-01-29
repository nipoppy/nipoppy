"""Parsers for the CLI."""
from argparse import ArgumentParser, HelpFormatter


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
        formatter_class=formatter_class,
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
    return parser
