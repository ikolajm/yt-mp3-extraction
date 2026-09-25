import argparse
from pathlib import Path
import sys

from .check_ffmpeg import has_ffmpeg
from .check_ytdlp import has_ytdlp

from .csv_utilities import read_requests
from .extraction import extract_mp3


def run_track(args: argparse.Namespace) -> int:
    if not has_ytdlp():
        return 1

    if not has_ffmpeg():
        return 1

    rows = read_requests(args.from_file)
    if rows is None:
        return 1

    try:
        args.out.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"Could not create directory `{args.out}`: {err}", file=sys.stderr)
        return 1

    failures = 0
    for row in rows:
        if not extract_mp3(row, args.out, args.timeout):
            failures += 1

    print(f"Extraction complete: {len(rows) - failures}/{len(rows)} downloaded.")
    if failures:
        print(f"{failures} of {len(rows)} rows failed to extract.", file=sys.stderr)

    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ytx",
        description="Download YouTube audio as MP3s."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    track_parser = subparsers.add_parser(
        "track",
        help="download each request as a single track"
    )
    track_parser.set_defaults(func=run_track)

    track_parser.add_argument(
        "--from-file",
        type=Path,
        default=Path("requests.csv"),
        help="CSV manifest of requests (default: ./requests.csv)",
    )

    track_parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "script-output",
        help="directory the mp3s are written to (default: ~/script-output)",
    )

    track_parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="allowed seconds until process timeout",
    )

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)

