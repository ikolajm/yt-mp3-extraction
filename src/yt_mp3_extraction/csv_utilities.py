import csv
import sys
from pathlib import Path

from .config import EXPECTED_COLUMNS
from .models import RequestRow


def read_requests(csv_path: Path) -> list[RequestRow] | None:
    """Parse `csv_path` into request rows.

    Returns None — having already explained why on stderr — if the file cannot
    be opened, the header does not match, or no usable rows are left.
    """
    try:
        csv_file = open(csv_path, newline="", encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"`{csv_path}` does not exist. Create it to proceed.", file=sys.stderr)
        return None
    except OSError as err:
        print(f"Could not open `{csv_path}`: {err}", file=sys.stderr)
        return None

    rows: list[RequestRow] = []
    invalid_count = 0

    with csv_file:
        csv_reader = csv.DictReader(csv_file)

        # Validate headers once, before doing any work.
        actual = set(csv_reader.fieldnames or [])
        if actual != EXPECTED_COLUMNS:
            missing = EXPECTED_COLUMNS - actual
            unexpected = actual - EXPECTED_COLUMNS
            print("CSV header mismatch:", file=sys.stderr)
            if missing:
                print(f"    Missing: {', '.join(sorted(missing))}", file=sys.stderr)
            if unexpected:
                print(f"    Unexpected: {', '.join(sorted(unexpected))}", file=sys.stderr)
            return None

        for row in csv_reader:
            # .get() because a short row yields None, which has no .strip()
            filename = (row.get("filename") or "").strip()
            youtube_link = (row.get("youtube_link") or "").strip()

            if not filename or not youtube_link:
                invalid_count += 1
                print(f"Skipping row {csv_reader.line_num}: missing filename or link.",
                      file=sys.stderr)
                continue

            rows.append(RequestRow(filename, youtube_link))

    if not rows:
        if invalid_count:
            print(f"No usable rows in `{csv_path}` ({invalid_count} invalid).",
                  file=sys.stderr)
        else:
            print(f"No requests found in `{csv_path}`.", file=sys.stderr)
        return None

    return rows
