"""Command line interface for csvdoctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from csvdoctor.core import profile_csv
from csvdoctor.report import to_json, to_markdown

_FORMATTERS = {
    "markdown": to_markdown,
    "json": to_json,
}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the csvdoctor CLI."""
    parser = argparse.ArgumentParser(
        prog="csvdoctor",
        description="Diagnose and clean CSV files.",
    )
    parser.add_argument("path", help="Path to the CSV file to inspect.")
    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(_FORMATTERS),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help="Write the report to FILE instead of stdout.",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=None,
        help="Field delimiter (default: sniff from the file).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the csvdoctor console script."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not Path(args.path).is_file():
        print(f"csvdoctor: error: no such file: {args.path}", file=sys.stderr)
        return 1

    profile = profile_csv(args.path, delimiter=args.delimiter)
    output = _FORMATTERS[args.format](profile)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0
