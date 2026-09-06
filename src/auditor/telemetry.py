"""Command-line telemetry snapshot output."""

import argparse
import json
from typing import Sequence

from auditor import __version__
from auditor.collector import collect_node_telemetry


def build_parser() -> argparse.ArgumentParser:
    """Build the parser used by the telemetry console script."""
    parser = argparse.ArgumentParser(
        description="Print a single Aurora Node Auditor telemetry snapshot as JSON."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Print a complete telemetry snapshot as formatted JSON."""
    build_parser().parse_args(argv)
    print(json.dumps(collect_node_telemetry(), indent=2))


if __name__ == "__main__":
    main()
