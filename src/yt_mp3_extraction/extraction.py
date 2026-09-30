import shutil
import sys
import tempfile
from pathlib import Path

from .cutting import CutError, check_times, cut
from .fetch import FetchError, download_audio, download_mp3
from .models import Track


def _place(staged: Path, final: Path) -> None:
    """Move a finished file from staging to its final path, making its folders."""
    final.parent.mkdir(parents=True, exist_ok=True)
    # replace, not rename: rename refuses an existing target on Windows.
    staged.replace(final)


def extract_link(tracks: list[Track], out_dir: Path) -> int:
    """Fetch one link once and place every one of its tracks not already there.

    Returns how many of the link's tracks failed.
    """
    link = tracks[0].link
    pending: list[Track] = []

    for t in tracks:
        if t.path.exists():
            print(f"Skipping {t.title!r}: {t.path.name} already exists.")
        else:
            pending.append(t)

    if not pending:
        return 0

    # Download, convert and cut in a staging directory and move each finished
    # track into place, so an interrupted run never leaves a partial file under
    # a final name for skip-if-exists to trust. Staging sits inside out_dir so
    # the move is a rename on one filesystem. ignore_cleanup_errors: after a
    # Ctrl+C on Windows, ffmpeg can still hold its output open, and the delete's
    # PermissionError would replace the KeyboardInterrupt main catches.
    with tempfile.TemporaryDirectory(
        dir=out_dir, ignore_cleanup_errors=True
    ) as staging:
        staging_dir = Path(staging)
        placed = 0

        try:
            if pending[0].start is None:
                download_mp3(link, staging_dir / "source.%(ext)s")
                mp3_out = staging_dir / "source.mp3"
                for i, track in enumerate(pending):
                    # Copy, never move: the next track copies from mp3_out too.
                    staged = staging_dir / f"{i}.mp3"
                    shutil.copyfile(mp3_out, staged)
                    _place(staged, track.path)
                    placed += 1
            else:
                source = download_audio(link, staging_dir)
                problems = check_times(tracks, source.duration)

                if problems:
                    for problem in problems:
                        print(problem, file=sys.stderr)
                    return len(pending)

                for i, track in enumerate(pending):
                    staged = staging_dir / f"{i}.mp3"
                    assert track.start is not None
                    cut(source.path, track.start, track.end, staged)
                    _place(staged, track.path)
                    placed += 1
        except (FetchError, CutError) as err:
            print(f"{link}: {err}", file=sys.stderr)
        return len(pending) - placed
