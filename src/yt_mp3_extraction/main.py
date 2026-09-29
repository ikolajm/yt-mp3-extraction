import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .check_ffmpeg import has_ffmpeg
from .csv_utilities import ManifestError, read_requests
from .extraction import extract_mp3


def run_get(args: argparse.Namespace) -> int:
    if not has_ffmpeg():
        return 1

    try:
        rows = read_requests(args.from_file)
    except ManifestError as err:
        print(f"Cannot run `{args.from_file}`:", file=sys.stderr)
        for problem in err.problems:
            print(f"    {problem}", file=sys.stderr)
        return 1

    try:
        args.out.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"Could not create directory `{args.out}`: {err}", file=sys.stderr)
        return 1

    failures = 0
    for row in rows:
        if not extract_mp3(row, args.out):
            failures += 1

    print(f"Extraction complete: {len(rows) - failures}/{len(rows)} downloaded.")
    if failures:
        print(f"{failures} of {len(rows)} rows failed to extract.", file=sys.stderr)

    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ytx", description="Download YouTube audio as MP3s."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser(
        "get", help="download every track the manifest describes"
    )
    get_parser.set_defaults(func=run_get)

    get_parser.add_argument(
        "--from-file",
        type=Path,
        default=Path("requests.csv"),
        help="CSV manifest of requests (default: ./requests.csv)",
    )

    get_parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "script-output",
        help="directory the mp3s are written to (default: ~/script-output)",
    )

    args = parser.parse_args(argv)
    try:
        func: Callable[[argparse.Namespace], int] = args.func
        return func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
