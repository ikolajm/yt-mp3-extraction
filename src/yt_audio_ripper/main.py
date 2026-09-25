import sys

from .check_ffmpeg import has_ffmpeg
from .check_ytdlp import has_ytdlp

from .config import CSV_PATH, SCRIPT_OUTPUT_DIR
from .csv_utilities import read_requests
from .extraction import extract_mp3


def main() -> int:
    if not has_ytdlp():
        return 1

    if not has_ffmpeg():
        return 1

    rows = read_requests(CSV_PATH)
    if rows is None:
        return 1

    try:
        SCRIPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"Could not create directory `{SCRIPT_OUTPUT_DIR}`: {err}", file=sys.stderr)
        return 1

    failures = 0
    for row in rows:
        if not extract_mp3(row):
            failures += 1

    print(f"Extraction complete: {len(rows) - failures}/{len(rows)} downloaded.")
    if failures:
        print(f"{failures} of {len(rows)} rows failed to extract.", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
