"""Parsers for the CLI."""
from argparse import ArgumentParser


def get_base_parser() -> ArgumentParser:
    """Get the base parser.

    Returns
    -------
    ArgumentParser
    """
    return ArgumentParser(prog="nipoppy")


def get_global_parser() -> ArgumentParser:
    """Get the global parser.

    Returns
    -------
    ArgumentParser
    """
    parser = get_base_parser()
    return parser
