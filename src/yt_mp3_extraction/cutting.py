import subprocess
from pathlib import Path

from .config import AUDIO_QUALITY
from .models import Track


class CutError(Exception):
    """Indicate error when cutting."""


def check_times(tracks: list[Track], duration: float) -> list[str]:
    """Return a problem for each slice that falls outside the video."""
    problems: list[str] = []

    for track in tracks:
        # `is not None`: a start of 0:00 is 0, which is falsy, and a last
        # slice with no end has None, meaning the end of the video.
        if track.start is not None and track.start >= duration:
            problems.append(
                f"{track.title!r}: starts at {track.start}s, "
                f"past the video's {duration:.0f}s"
            )
        elif track.end is not None and track.end > duration:
            problems.append(
                f"{track.title!r}: ends at {track.end}s, "
                f"past the video's {duration:.0f}s"
            )

    return problems


def cut(source: Path, start: int, end: int | None, target: Path) -> None:
    """Encode source from start to end (or its end) as an mp3 at target."""
    # -ss before -i seeks the input, which is fast and, since the cut
    # re-encodes, accurate. Next to that seek, -t gives a duration, not an end.
    args = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-i",
        str(source),
    ]
    if end is not None:
        args += ["-t", str(end - start)]
    args += ["-vn", "-acodec", "libmp3lame", "-q:a", AUDIO_QUALITY, str(target)]

    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as err:
        raise CutError(f"ffmpeg could not cut {target.name}") from err
