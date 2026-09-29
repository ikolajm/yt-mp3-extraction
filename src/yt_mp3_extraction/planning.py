from collections import defaultdict
from itertools import groupby
from pathlib import Path

from .csv_utilities import ManifestError
from .models import RequestRow, Track
from .naming import album_track_path, sanitize_filename, single_path


def _album_key(row: RequestRow) -> tuple[str, str] | None:
    """The album a row belongs to, or None for a single.

    The key is the pair of folders the album lands in, casefolded: NTFS
    ignores case, so `Live EP` and `live ep` are one folder and one album.
    """
    if row.album is None:
        return None
    return (
        sanitize_filename(row.artist).casefold(),
        sanitize_filename(row.album).casefold(),
    )


def plan_tracks(rows: list[RequestRow], out_dir: Path) -> list[Track]:
    """Turn manifest rows into the tracks they describe, with no network.

    Raises ManifestError carrying every problem found, each as `Row N: ...`.
    """
    tracks: list[Track] = []
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()

    # Every row of each link, wherever it sits: whole-video rows of one link
    # may be far apart, which groupby would not see.
    by_link: defaultdict[str, list[RequestRow]] = defaultdict(list)
    for row in rows:
        by_link[row.youtube_link].append(row)

    for link_rows in by_link.values():
        # `is not None`: a first slice at 0:00 has a start of 0, which is falsy.
        if not any(row.start is not None for row in link_rows):
            continue
        for row in link_rows:
            if row.start is None:
                problems.append(
                    f"Row {row.line}: this link has slices, "
                    "so every row for it needs a start"
                )
            elif row.album is None:
                problems.append(f"Row {row.line}: a slice needs an album")
        # The key holds the artist too, so this covers both.
        if len({_album_key(row) for row in link_rows}) > 1:
            problems.append(
                f"Row {link_rows[0].line}: slices of one link must share "
                "one artist and one album"
            )

    # Each file path already planned, casefolded, and the row that took it.
    taken: dict[str, int] = {}

    # groupby only joins neighbours, so an album key that comes back later
    # starts a second group: an album split by other rows. Singles all have
    # the key None and are planned one by one.
    for key, group in groupby(rows, key=_album_key):
        group_rows = list(group)
        first = group_rows[0]
        # True when the group is one video's slices, all with a start.
        has_times = False

        if key is not None:
            if key in seen:
                problems.append(
                    f"Row {first.line}: album {first.album!r} by {first.artist} "
                    "continues after other rows; keep an album's rows together"
                )
            seen.add(key)

            # One video is one album, so its tracks have a single home.
            is_sliced = any(row.start is not None for row in group_rows)
            one_link = len({row.youtube_link for row in group_rows}) == 1
            if is_sliced and not one_link:
                problems.append(
                    f"Row {first.line}: an album with slices holds only that video"
                )
            # A link mixing slices and whole rows is refused above; skipping
            # the time rules for it keeps a start of None out of them.
            has_times = one_link and all(row.start is not None for row in group_rows)

        for number, row in enumerate(group_rows, start=1):
            end = row.end
            if has_times:
                assert row.start is not None
                # number counts from 1, so group_rows[number] is the next row.
                next_row = group_rows[number] if number < len(group_rows) else None
                next_start = next_row.start if next_row is not None else None

                # `is not None` throughout: a time of 0:00 is 0, which is falsy.
                if (
                    next_row is not None
                    and next_start is not None
                    and next_start <= row.start
                ):
                    problems.append(
                        f"Row {next_row.line}: start must be after "
                        "the previous slice's start"
                    )
                if row.end is not None and row.end <= row.start:
                    problems.append(f"Row {row.line}: end must be after start")
                if (
                    row.end is not None
                    and next_start is not None
                    and row.end > next_start
                ):
                    problems.append(
                        f"Row {row.line}: end passes the next slice's start"
                    )
                # None on a last slice with no end: the end of the video,
                # which only the download knows.
                end = row.end if row.end is not None else next_start

            try:
                if key is None:
                    path = single_path(out_dir, row.artist, row.title)
                else:
                    # The first row's spelling for every track: `Live EP` and
                    # `live ep` are one album, and must be one folder on Linux.
                    assert first.album is not None
                    path = album_track_path(
                        out_dir,
                        first.artist,
                        first.album,
                        number,
                        len(group_rows),
                        row.title,
                    )
            except ValueError as err:
                problems.append(f"Row {row.line}: {err}")
                continue

            # Casefolded, since NTFS treats Song.mp3 and song.mp3 as one file.
            claim = str(path).casefold()
            if claim in taken:
                problems.append(
                    f"Row {row.line}: plans to the same file as row "
                    f"{taken[claim]}: {path.as_posix()}"
                )
            else:
                taken[claim] = row.line

            tracks.append(
                Track(
                    path=path,
                    title=row.title,
                    artist=row.artist if key is None else first.artist,
                    album=None if key is None else first.album,
                    track_number=None if key is None else number,
                    link=row.youtube_link,
                    start=row.start,
                    end=end,
                )
            )

    if problems:
        raise ManifestError(problems)
    return tracks
