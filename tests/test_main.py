import pytest

from yt_mp3_extraction import main as main_module
from yt_mp3_extraction.models import RequestRow

HEADER = "filename,youtube_link\n"


class TestMain:

    @pytest.fixture
    def wired(self, monkeypatch, tmp_path):
        """Sandbox main(): deps present, paths in tmp_path, no downloads.

        The fake fails any row named FAIL*.
        """
        csv_path = tmp_path / "requests.csv"
        output_dir = tmp_path / "out"
        downloaded = []

        def fake_extract(row: RequestRow) -> bool:
            downloaded.append(row)
            return not row.filename.startswith("FAIL")

        monkeypatch.setattr(main_module, "has_ytdlp", lambda: True)
        monkeypatch.setattr(main_module, "has_ffmpeg", lambda: True)
        monkeypatch.setattr(main_module, "CSV_PATH", csv_path)
        monkeypatch.setattr(main_module, "SCRIPT_OUTPUT_DIR", output_dir)
        monkeypatch.setattr(main_module, "extract_mp3", fake_extract)

        return {"csv": csv_path, "output_dir": output_dir, "downloaded": downloaded}

    def test_happy_path_exits_0(self, wired):
        wired["csv"].write_text(HEADER + "Song One,https://a\nSong Two,https://b\n")

        assert main_module.main() == 0
        assert [r.filename for r in wired["downloaded"]] == ["Song One", "Song Two"]
        assert wired["output_dir"].is_dir()

    def test_any_failure_exits_1(self, capsys, wired):
        wired["csv"].write_text(HEADER + "OK,https://a\nFAIL Two,https://b\n")

        assert main_module.main() == 1
        assert "1/2 downloaded" in capsys.readouterr().out

    def test_bad_csv_does_not_create_the_output_dir(self, wired):
        """Ordering: validate before creating anything on disk."""
        wired["csv"].write_text("wrong_header\nA\n")

        assert main_module.main() == 1
        assert not wired["output_dir"].exists()

    @pytest.mark.parametrize("missing_dep", ["has_ytdlp", "has_ffmpeg"])
    def test_missing_dependency_exits_1_before_reading_anything(
        self, monkeypatch, wired, missing_dep
    ):
        monkeypatch.setattr(main_module, missing_dep, lambda: False)

        assert main_module.main() == 1
        assert wired["downloaded"] == []
