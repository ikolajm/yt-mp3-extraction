from collections.abc import Callable
from pathlib import Path

import pytest

from yt_mp3_extraction.csv_utilities import ManifestError, parse_time, read_requests
from yt_mp3_extraction.models import RequestRow

HEADER = "youtube_link,title,artist,album,start,end\n"

# The example from the backlog's Shape section: singles, an album, and one
# video cut into an album.
SHAPE_EXAMPLE = """\
youtube_link,title,artist,album,start,end
https://youtu.be/AAA,Song One,Some Band,,,
https://youtu.be/BBB,Opener,Other Band,Live EP,,
https://youtu.be/CCC,Closer,Other Band,Live EP,,
https://youtu.be/DDD,Bulls on Parade,RATM,Evil Empire,0:00,
https://youtu.be/DDD,Vietnow,RATM,Evil Empire,3:52,
https://youtu.be/DDD,Revolver,RATM,Evil Empire,8:30,13:05
"""


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[[str], Path]:
    def _write(content: str) -> Path:
        path = tmp_path / "requests.csv"
        path.write_text(content, encoding="utf-8")
        return path

    return _write


class TestParseTime:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("0:00", 0),
            ("3:52", 232),
            ("3:59", 239),
            ("13:05", 785),
            ("75:30", 4530),
            ("1:02:03", 3723),
        ],
    )
    def test_converts_to_seconds(self, text: str, expected: int) -> None:
        assert parse_time(text) == expected

    @pytest.mark.parametrize(
        "text",
        ["", "3:5", "3:60", "1:60:00", "abc", "1:2:3:4", "-1:00", "1:2:03", "3:²5"],
    )
    def test_refuses_malformed_times(self, text: str) -> None:
        with pytest.raises(ValueError, match="not M:SS or H:MM:SS"):
            parse_time(text)


class TestReadRequests:
    def test_parses_a_row_stripping_every_cell(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        rows = read_requests(
            write_csv(HEADER + "  https://a  ,  Song One  ,  Some Band  , , , \n")
        )

        assert rows == [RequestRow("https://a", "Song One", "Some Band", line=2)]

    def test_reads_the_shape_example(self, write_csv: Callable[[str], Path]) -> None:
        rows = read_requests(write_csv(SHAPE_EXAMPLE))

        assert rows == [
            RequestRow("https://youtu.be/AAA", "Song One", "Some Band", line=2),
            RequestRow(
                "https://youtu.be/BBB", "Opener", "Other Band", "Live EP", line=3
            ),
            RequestRow(
                "https://youtu.be/CCC", "Closer", "Other Band", "Live EP", line=4
            ),
            RequestRow(
                "https://youtu.be/DDD",
                "Bulls on Parade",
                "RATM",
                "Evil Empire",
                0,
                line=5,
            ),
            RequestRow(
                "https://youtu.be/DDD", "Vietnow", "RATM", "Evil Empire", 232, line=6
            ),
            RequestRow(
                "https://youtu.be/DDD",
                "Revolver",
                "RATM",
                "Evil Empire",
                510,
                785,
                line=7,
            ),
        ]

    def test_optional_columns_may_be_left_out(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        rows = read_requests(
            write_csv("youtube_link,title,artist\nhttps://a,Song One,Some Band\n")
        )

        assert rows == [RequestRow("https://a", "Song One", "Some Band", line=2)]

    def test_a_bad_row_refuses_the_whole_manifest(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        """Every problem is reported, and the good row is not returned alone."""
        body = (
            "https://a,Good,Some Band,,,\n"
            "https://b,No Artist,,,,\n"
            "https://c,Short Row\n"
            "https://d,Bad Time,Some Band,,3:5,\n"
        )

        with pytest.raises(ManifestError) as exc_info:
            read_requests(write_csv(HEADER + body))

        assert exc_info.value.problems == [
            "Row 3: missing artist",
            "Row 4: missing artist",
            "Row 5: start time '3:5' is not M:SS or H:MM:SS",
        ]

    def test_end_without_start_is_refused(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        with pytest.raises(ManifestError) as exc_info:
            read_requests(write_csv(HEADER + "https://a,Song,Band,,,3:00\n"))

        assert exc_info.value.problems == ["Row 2: end given without a start"]

    def test_a_malformed_start_is_not_also_reported_missing(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        with pytest.raises(ManifestError) as exc_info:
            read_requests(write_csv(HEADER + "https://a,Song,Band,,3:5,4:00\n"))

        assert exc_info.value.problems == [
            "Row 2: start time '3:5' is not M:SS or H:MM:SS"
        ]

    def test_a_start_of_zero_counts_as_given(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        """0 is falsy, so a truthiness check on the parsed start refuses it."""
        rows = read_requests(write_csv(HEADER + "https://a,Song,Band,,0:00,3:52\n"))

        assert rows == [
            RequestRow("https://a", "Song", "Band", start=0, end=232, line=2)
        ]

    def test_extra_cells_are_refused(self, write_csv: Callable[[str], Path]) -> None:
        """An unquoted comma in a title, which shifts every cell after it."""
        with pytest.raises(ManifestError) as exc_info:
            read_requests(write_csv(HEADER + "https://a,Hello, World,Band,,,,\n"))

        assert exc_info.value.problems == [
            "Row 2: more cells than columns; quote a value with a comma"
        ]

    def test_a_manifest_with_no_rows_is_refused(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        with pytest.raises(ManifestError, match="No requests found"):
            read_requests(write_csv(HEADER))

    def test_a_row_carries_the_line_it_ends_on(
        self, write_csv: Callable[[str], Path]
    ) -> None:
        rows = read_requests(
            write_csv(
                HEADER
                + 'https://a,"Track A\n",Band A,Album A\n'
                + "https://b,Track B,Band B,Album B\n"
            )
        )

        assert rows[1].line == 4

    @pytest.mark.parametrize(
        "header, expected",
        [
            ("youtube_link,title\n", ["Missing column: artist"]),
            (
                "youtube_link,title,artist,extra\n",
                ["Unexpected column: extra"],
            ),
            (
                "filename,youtube_link\n",
                ["Missing column: artist, title", "Unexpected column: filename"],
            ),
            (
                "youtube_link,title,artist,title\n",
                ["Duplicate column: title"],
            ),
        ],
        ids=["missing-column", "unknown-column", "old-header", "duplicate-column"],
    )
    def test_refuses_bad_headers(
        self,
        write_csv: Callable[[str], Path],
        header: str,
        expected: list[str],
    ) -> None:
        with pytest.raises(ManifestError) as exc_info:
            read_requests(write_csv(header + "https://a,Song,Band,Extra\n"))

        assert exc_info.value.problems == expected

    def test_missing_file_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError, match="does not exist"):
            read_requests(tmp_path / "nope.csv")

    def test_unopenable_path_is_reported(self, tmp_path: Path) -> None:
        """The case an `if path.exists()` pre-check would wave through.

        A directory where the CSV should be, rather than a file with its
        permissions taken away. `chmod` cannot remove read on NT — it toggles
        the read-only bit, so 0o000 lands at 0o444 and the file opens fine.
        Opening a directory fails under both kernels, as IsADirectoryError on
        POSIX and PermissionError on NT, and neither is FileNotFoundError, so
        the same branch is reached whichever machine runs this.
        """
        path = tmp_path / "requests.csv"
        path.mkdir()

        with pytest.raises(ManifestError, match="Could not read"):
            read_requests(path)

    def test_a_manifest_that_is_not_utf8_is_reported(self, tmp_path: Path) -> None:
        """What Excel's plain "CSV" save writes: cp1252, where é is one byte."""
        path = tmp_path / "requests.csv"
        path.write_bytes((HEADER + "https://a,Café,Band,,,\n").encode("cp1252"))

        with pytest.raises(ManifestError, match="is not UTF-8"):
            read_requests(path)
