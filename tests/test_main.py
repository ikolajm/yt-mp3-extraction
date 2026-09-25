from pathlib import Path

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
        seen = {}
        timeout = 7

        def fake_extract(row: RequestRow, out_dir: Path, timeout: int) -> bool:
            downloaded.append(row)
            seen["out_dir"] = out_dir
            seen["timeout"] = timeout
            return not row.filename.startswith("FAIL")

        monkeypatch.setattr(main_module, "has_ytdlp", lambda: True)
        monkeypatch.setattr(main_module, "has_ffmpeg", lambda: True)
        monkeypatch.setattr(main_module, "extract_mp3", fake_extract)

        return {
            "argv": [
                "track",
                "--from-file", str(csv_path),
                "--out", str(output_dir),
                "--timeout", str(timeout)
            ],
            "csv": csv_path,
            "output_dir": output_dir,
            "downloaded": downloaded,
            "seen": seen,
            "timeout": timeout
        }

    def test_happy_path_exits_0(self, wired):
        wired["csv"].write_text(HEADER + "Song One,https://a\nSong Two,https://b\n")

        assert main_module.main(wired["argv"]) == 0
        assert [r.filename for r in wired["downloaded"]] == ["Song One", "Song Two"]
        assert wired["seen"]["out_dir"] == wired["output_dir"]
        assert wired["seen"]["timeout"] == wired["timeout"]
        assert wired["output_dir"].is_dir()

    def test_any_failure_exits_1(self, capsys, wired):
        wired["csv"].write_text(HEADER + "OK,https://a\nFAIL Two,https://b\n")

        assert main_module.main(wired["argv"]) == 1
        assert "1/2 downloaded" in capsys.readouterr().out

    def test_bad_csv_does_not_create_the_output_dir(self, wired):
        """Ordering: validate before creating anything on disk."""
        wired["csv"].write_text("wrong_header\nA\n")

        assert main_module.main(wired["argv"]) == 1
        assert not wired["output_dir"].exists()

    @pytest.mark.parametrize("missing_dep", ["has_ytdlp", "has_ffmpeg"])
    def test_missing_dependency_exits_1_before_reading_anything(
        self, monkeypatch, wired, missing_dep
    ):
        monkeypatch.setattr(main_module, missing_dep, lambda: False)

        assert main_module.main(wired["argv"]) == 1
        assert wired["downloaded"] == []

    def test_no_subcommand_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            main_module.main([])
        assert exc.value.code == 2

    def test_help_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main_module.main(["--help"])
        assert exc.value.code == 0
        assert "track" in capsys.readouterr().out
