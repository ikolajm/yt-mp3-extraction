import pytest

from yt_mp3_extraction.naming import MAX_STEM_BYTES, sanitize_filename


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Simple Name", "Simple_Name"),
        ("keeps-hyphens", "keeps-hyphens"),
        ("collapses   runs", "collapses_runs"),
        ("_strips_edges_", "strips_edges"),
        ("Ünïcødé Nâme", "Ünïcødé_Nâme"),
    ],
)
def test_rewrites_names(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


@pytest.mark.parametrize("attack", ["../../etc/passwd", "/etc/passwd", "..", "a/b/c"])
def test_strips_path_separators(attack: str) -> None:
    """A stem must never be able to escape the output directory."""
    result = sanitize_filename(attack)

    assert "/" not in result
    assert ".." not in result


@pytest.mark.parametrize("empty", ["", "...", "   ", "///", "___"])
def test_returns_empty_when_nothing_usable(empty: str) -> None:
    assert sanitize_filename(empty) == ""


@pytest.mark.parametrize("char", ["x", "é"])
def test_caps_length_in_bytes_not_characters(char: str) -> None:
    """A 2-byte character must not produce a 2x-oversized filename."""
    result = sanitize_filename(char * 300)

    assert result
    assert len(result.encode("utf-8")) <= MAX_STEM_BYTES
