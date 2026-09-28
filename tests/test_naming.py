from pathlib import Path

import pytest

from yt_mp3_extraction.config import AUDIO_FORMAT
from yt_mp3_extraction.naming import (
    MAX_STEM_BYTES,
    album_track_path,
    sanitize_filename,
    single_path,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Simple Name", "Simple Name"),
        ("keeps-hyphens_and_underscores", "keeps-hyphens_and_underscores"),
        ("___", "___"),
        ("collapses   runs", "collapses runs"),
        ("  strips edges  ", "strips edges"),
        ("tab\tbecomes a space", "tab becomes a space"),
        ("line\nbreak", "line break"),
        ("Ünïcødé Nâme", "Ünïcødé Nâme"),
        ("AC/DC", "ACDC"),
        # Removing a character can leave two spaces behind.
        ("Who? What : Why", "Who What Why"),
        ("trailing dot.", "trailing dot"),
        ("trailing . .", "trailing"),
        ("...And Justice for All", "...And Justice for All"),
    ],
)
def test_rewrites_names(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


@pytest.mark.parametrize("char", [*'<>:"/\\|?*', "\x00", "\x07", "\x1b"])
def test_removes_refused_characters(char: str) -> None:
    assert sanitize_filename(f"a{char}b") == "ab"


@pytest.mark.parametrize(
    "attack",
    ["../../etc/passwd", "/etc/passwd", "..", ".", "a/b/c", "..\\..\\Windows", "C:\\x"],
)
def test_result_is_a_single_path_component(attack: str) -> None:
    """A name must never be able to escape the directory it is joined onto."""
    result = sanitize_filename(attack)

    assert "/" not in result
    assert "\\" not in result
    assert result not in {".", ".."}


@pytest.mark.parametrize("empty", ["", "...", "   ", ". .", "///", "?*", "\x00\x01"])
def test_returns_empty_when_nothing_usable(empty: str) -> None:
    assert sanitize_filename(empty) == ""


@pytest.mark.parametrize("char", ["x", "é"])
def test_caps_length_in_bytes_not_characters(char: str) -> None:
    """A 2-byte character must not produce a 2x-oversized filename."""
    result = sanitize_filename(char * 300)

    assert result
    assert len(result.encode("utf-8")) <= MAX_STEM_BYTES


@pytest.mark.parametrize("separator", [" ", ".", ". "])
def test_strips_what_the_cap_leaves_trailing(separator: str) -> None:
    """The cut can land just after a space or dot; that must not end the name."""
    stem = "x" * (MAX_STEM_BYTES - len(separator))

    assert sanitize_filename(f"{stem}{separator}rest") == stem


OUT = Path("out")


def test_single_lands_under_its_artist() -> None:
    assert single_path(OUT, "Some Band", "Song One") == (
        OUT / "Some Band" / f"Song One.{AUDIO_FORMAT}"
    )


def test_album_track_lands_under_artist_and_album() -> None:
    assert album_track_path(OUT, "Other Band", "Live EP", 1, 2, "Opener") == (
        OUT / "Other Band" / "Live EP" / f"01 - Opener.{AUDIO_FORMAT}"
    )


@pytest.mark.parametrize(
    "number, album_size, prefix",
    [
        (1, 1, "01"),
        (7, 99, "07"),
        (7, 100, "007"),
        (100, 100, "100"),
        (7, 1000, "0007"),
    ],
)
def test_numbers_widen_past_99_so_names_still_sort(
    number: int, album_size: int, prefix: str
) -> None:
    path = album_track_path(OUT, "A", "B", number, album_size, "T")

    assert path.name == f"{prefix} - T.{AUDIO_FORMAT}"


def test_same_album_name_under_two_artists_is_two_albums() -> None:
    first = album_track_path(OUT, "Band One", "Greatest Hits", 1, 1, "T")
    second = album_track_path(OUT, "Band Two", "Greatest Hits", 1, 1, "T")

    assert first.parent != second.parent


def test_every_part_is_sanitized() -> None:
    assert album_track_path(OUT, "AC/DC", "Who? Me", 1, 1, "Part 1: Go.") == (
        OUT / "ACDC" / "Who Me" / f"01 - Part 1 Go.{AUDIO_FORMAT}"
    )


def test_no_part_escapes_the_out_dir(tmp_path: Path) -> None:
    path = album_track_path(tmp_path, "../../a", "..\\b", 1, 1, "../c")

    assert path.resolve().is_relative_to(tmp_path.resolve())
    assert len(path.relative_to(tmp_path).parts) == 3


@pytest.mark.parametrize("field", ["artist", "album", "title"])
def test_album_track_refuses_a_part_left_empty(field: str) -> None:
    parts = {"artist": "A", "album": "B", "title": "T", field: "..."}

    with pytest.raises(ValueError, match=field):
        album_track_path(OUT, parts["artist"], parts["album"], 1, 1, parts["title"])


@pytest.mark.parametrize("field", ["artist", "title"])
def test_single_refuses_a_part_left_empty(field: str) -> None:
    parts = {"artist": "A", "title": "T", field: "?*"}

    with pytest.raises(ValueError, match=field):
        single_path(OUT, parts["artist"], parts["title"])
