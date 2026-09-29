import csv
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .config import OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from .models import RequestRow


def parse_time(text: str) -> int:
    """Convert `M:SS` or `H:MM:SS` to seconds.

    The leading field is any number of digits, so `75:30` is valid; every field
    after it is exactly two digits no greater than 59. Raises ValueError on
    anything else.
    """
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"time {text!r} is not M:SS or H:MM:SS")

    # [0-9] rather than \d, which also matches non-ASCII digits like '²'.
    leading, *rest = parts
    if not re.fullmatch(r"[0-9]+", leading):
        raise ValueError(f"time {text!r} is not M:SS or H:MM:SS")
    for part in rest:
        if not re.fullmatch(r"[0-9]{2}", part) or int(part) > 59:
            raise ValueError(f"time {text!r} is not M:SS or H:MM:SS")

    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total


class ManifestError(Exception):
    """A manifest that cannot be run, carrying every problem found in it."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def _header_problems(fieldnames: Sequence[str] | None) -> list[str]:
    """Everything wrong with the header, or an empty list if nothing is."""
    names = list(fieldnames or [])
    actual = set(names)
    problems = []

    # Checked on the list: the set below has already lost the duplicate, and
    # DictReader would silently keep the last column's value.
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        problems.append(f"Duplicate column: {', '.join(duplicated)}")

    missing = REQUIRED_COLUMNS - actual
    if missing:
        problems.append(f"Missing column: {', '.join(sorted(missing))}")

    unexpected = actual - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
    if unexpected:
        problems.append(f"Unexpected column: {', '.join(sorted(unexpected))}")

    return problems


def _parse_row(row: Mapping[str | None, Any]) -> RequestRow:
    """Build one request from a CSV row.

    Raises ManifestError carrying every problem in the row, so one run reports
    them all rather than the first.
    """
    # DictReader files cells past the last column under the key None. It is
    # usually an unquoted comma in a title, which shifts every cell after it.
    if None in row:
        raise ManifestError(["more cells than columns; quote a value with a comma"])

    # A short row yields None for its missing cells, which has no .strip().
    cells = {
        column: (row.get(column) or "").strip()
        for column in REQUIRED_COLUMNS | OPTIONAL_COLUMNS
    }

    problems = [
        f"missing {column}" for column in sorted(REQUIRED_COLUMNS) if not cells[column]
    ]

    times: dict[str, int | None] = {"start": None, "end": None}
    for column in times:
        if cells[column]:
            try:
                times[column] = parse_time(cells[column])
            except ValueError as err:
                problems.append(f"{column} {err}")

    # On the cells, not the parsed times, so a malformed start is not also
    # reported as a missing one.
    if cells["end"] and not cells["start"]:
        problems.append("end given without a start")

    if problems:
        raise ManifestError(problems)

    return RequestRow(
        youtube_link=cells["youtube_link"],
        title=cells["title"],
        artist=cells["artist"],
        album=cells["album"] or None,
        start=times["start"],
        end=times["end"],
    )


def read_requests(csv_path: Path) -> list[RequestRow]:
    """Parse `csv_path` into request rows.

    Raises ManifestError if the file cannot be read, the header is wrong, any
    row is invalid, or no rows are left. One bad row refuses the whole
    manifest: skipping it would stretch the slice before it or renumber its
    album, and neither would be visible in the output.
    """
    rows: list[RequestRow] = []
    problems: list[str] = []

    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as csv_file:
            csv_reader = csv.DictReader(csv_file)

            # Rows cannot be read against a wrong header, so it fails alone.
            header_problems = _header_problems(csv_reader.fieldnames)
            if header_problems:
                raise ManifestError(header_problems)

            for row in csv_reader:
                try:
                    rows.append(_parse_row(row))
                except ManifestError as err:
                    line = csv_reader.line_num
                    problems.extend(
                        f"Row {line}: {problem}" for problem in err.problems
                    )
    except FileNotFoundError as err:
        message = f"`{csv_path}` does not exist. Create it to proceed."
        raise ManifestError([message]) from err
    except OSError as err:
        raise ManifestError([f"Could not read `{csv_path}`: {err}"]) from err

    if problems:
        raise ManifestError(problems)
    if not rows:
        raise ManifestError([f"No requests found in `{csv_path}`."])

    return rows
