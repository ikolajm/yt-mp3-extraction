import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .check_ffmpeg import has_ffmpeg
from .csv_utilities import ManifestError, read_requests
from .extraction import extract_link
from .models import Track
from .planning import plan_tracks


def run_get(args: argparse.Namespace) -> int:
    if not has_ffmpeg():
        return 1

    try:
        rows = read_requests(args.from_file)
        tracks = plan_tracks(rows, args.out)
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

    by_link: dict[str, list[Track]] = {}
    for track in tracks:
        by_link.setdefault(track.link, []).append(track)

    failures = 0
    for link_tracks in by_link.values():
        failures += extract_link(link_tracks, args.out)

    print(
        f"Extraction complete: {len(tracks) - failures}/{len(tracks)} tracks in place."
    )
    if failures:
        print(f"{failures} of {len(tracks)} tracks failed to extract.", file=sys.stderr)

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
