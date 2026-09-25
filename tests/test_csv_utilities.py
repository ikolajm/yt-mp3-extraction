import pytest

from yt_mp3_extraction.csv_utilities import read_requests
from yt_mp3_extraction.models import RequestRow

HEADER = "filename,youtube_link\n"


@pytest.fixture
def write_csv(tmp_path):
    def _write(content: str):
        path = tmp_path / "requests.csv"
        path.write_text(content, encoding="utf-8")
        return path
    return _write


class TestReadRequests:

    def test_parses_rows_into_requestrow_objects(self, write_csv):
        rows = read_requests(write_csv(HEADER + "  Song One  ,  https://a  \n"))

        assert rows == [RequestRow("Song One", "https://a")]
        assert isinstance(rows[0], RequestRow)

    def test_reads_every_row(self, write_csv):
        body = "".join(f"Song {i},https://{i}\n" for i in range(5))

        assert len(read_requests(write_csv(HEADER + body))) == 5

    def test_skips_rows_missing_a_field(self, capsys, write_csv):
        rows = read_requests(write_csv(HEADER + "Good,https://a\n,https://b\nNoLink,\n"))

        assert rows == [RequestRow("Good", "https://a")]
        assert "Skipping row 3" in capsys.readouterr().err

    @pytest.mark.parametrize("header, expected_fragments", [
        ("file_name,link\n",              ["Missing", "Unexpected"]),
        ("filename\n",                    ["Missing", "youtube_link"]),
        ("filename,youtube_link,extra\n", ["Unexpected", "extra"]),
    ], ids=["both-wrong", "missing-column", "extra-column"])
    def test_rejects_bad_headers(self, capsys, write_csv, header, expected_fragments):
        assert read_requests(write_csv(header + "A,https://a\n")) is None

        err = capsys.readouterr().err
        for fragment in expected_fragments:
            assert fragment in err

    def test_missing_file_is_reported(self, tmp_path, capsys):
        assert read_requests(tmp_path / "nope.csv") is None
        assert "does not exist" in capsys.readouterr().err

    def test_unopenable_path_is_reported(self, capsys, tmp_path):
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

        assert read_requests(path) is None
        assert "Could not open" in capsys.readouterr().err
