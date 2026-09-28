import re
from pathlib import Path

from .config import AUDIO_FORMAT

# ext4 and most Linux filesystems cap a filename component at 255 bytes.
# Leave headroom for the extension and an album track's "NN - " prefix.
MAX_STEM_BYTES = 240

# Characters some filesystem refuses in a name. Linux refuses only `/` and NUL;
# the rest are Windows', removed everywhere so a name is valid on both.
_REFUSED = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _truncate_bytes(text: str, limit: int) -> str:
    """Cut `text` to at most `limit` UTF-8 bytes without splitting a character."""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def sanitize_filename(name: str) -> str:
    """Reduce a name to a single path component valid on Windows and Linux.

    Spaces are kept. Refused characters are removed, whitespace collapses to
    single spaces, and trailing dots and spaces are stripped. No separator
    survives and `.` and `..` strip to nothing, so the result can never escape
    the directory it is joined onto.

    The result is capped at MAX_STEM_BYTES so a long name fails cleanly here
    rather than as an ENAMETOOLONG from yt-dlp. Returns "" if nothing usable
    is left.
    """
    # Whitespace first, so a tab becomes a space instead of being removed with
    # the other control characters.
    text = re.sub(r"\s", " ", name)
    text = _REFUSED.sub("", text)
    # split() with no argument also drops leading and trailing whitespace.
    text = " ".join(text.split())
    # Windows drops trailing dots and spaces itself, so `a.` and `a` collide.
    # Stripped after the cut, which can expose a new one.
    return _truncate_bytes(text, MAX_STEM_BYTES).rstrip(". ")


def _component(value: str, field: str) -> str:
    """Sanitize one part of a track's path, refusing one left empty.

    An empty artist or album would not fail on its own: the file would land a
    level higher than it belongs.
    """
    component = sanitize_filename(value)
    if not component:
        raise ValueError(f"{field} {value!r} has no usable filename characters")
    return component


def single_path(out_dir: Path, artist: str, title: str) -> Path:
    """Where a track outside any album lands: `Artist/Title.mp3`."""
    return (
        out_dir
        / _component(artist, "artist")
        / f"{_component(title, 'title')}.{AUDIO_FORMAT}"
    )


def album_track_path(
    out_dir: Path, artist: str, album: str, number: int, album_size: int, title: str
) -> Path:
    """Where an album track lands: `Artist/Album/NN - Title.mp3`.

    The number is two digits, widened to the album size's width so names
    still sort past 99 tracks.
    """
    width = max(2, len(str(album_size)))
    name = f"{str(number).zfill(width)} - {_component(title, 'title')}.{AUDIO_FORMAT}"
    return out_dir / _component(artist, "artist") / _component(album, "album") / name
