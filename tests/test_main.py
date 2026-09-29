from pathlib import Path
from typing import Any

import pytest

from yt_mp3_extraction import main as main_module
from yt_mp3_extraction.models import RequestRow

HEADER = "youtube_link,title,artist\n"


class TestMain:
    @pytest.fixture
    def wired(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
        """Sandbox main(): deps present, paths in tmp_path, no downloads.

        The fake fails any row named FAIL*.
        """
        csv_path = tmp_path / "requests.csv"
        output_dir = tmp_path / "out"
        downloaded = []
        seen: dict[str, Any] = {}

        def fake_extract(row: RequestRow, out_dir: Path) -> bool:
            downloaded.append(row)
            seen["out_dir"] = out_dir
            return not row.title.startswith("FAIL")

        monkeypatch.setattr(main_module, "has_ffmpeg", lambda: True)
        monkeypatch.setattr(main_module, "extract_mp3", fake_extract)

        return {
            "argv": [
                "get",
                "--from-file",
                str(csv_path),
                "--out",
                str(output_dir),
            ],
            "csv": csv_path,
            "output_dir": output_dir,
            "downloaded": downloaded,
            "seen": seen,
        }

    def test_happy_path_exits_0(self, wired: dict[str, Any]) -> None:
        wired["csv"].write_text(
            HEADER + "https://a,Song One,Some Band\nhttps://b,Song Two,Some Band\n"
        )

        assert main_module.main(wired["argv"]) == 0
        assert [r.title for r in wired["downloaded"]] == ["Song One", "Song Two"]
        assert wired["seen"]["out_dir"] == wired["output_dir"]
        assert wired["output_dir"].is_dir()

    def test_any_failure_exits_1(
        self, capsys: pytest.CaptureFixture[str], wired: dict[str, Any]
    ) -> None:
        wired["csv"].write_text(
            HEADER + "https://a,OK,Some Band\nhttps://b,FAIL Two,Some Band\n"
        )

        assert main_module.main(wired["argv"]) == 1
        assert "1/2 downloaded" in capsys.readouterr().out

    def test_bad_csv_is_reported_and_creates_nothing(
        self, capsys: pytest.CaptureFixture[str], wired: dict[str, Any]
    ) -> None:
        """Ordering: validate before creating anything on disk."""
        wired["csv"].write_text(HEADER + "https://a,,Some Band\nhttps://b,Song,\n")

        assert main_module.main(wired["argv"]) == 1
        assert not wired["output_dir"].exists()
        assert wired["downloaded"] == []

        # Every problem reaches the user, not only the first.
        err = capsys.readouterr().err
        assert "Row 2: missing title" in err
        assert "Row 3: missing artist" in err

    def test_missing_ffmpeg_exits_1_before_reading_anything(
        self, monkeypatch: pytest.MonkeyPatch, wired: dict[str, Any]
    ) -> None:
        monkeypatch.setattr(main_module, "has_ffmpeg", lambda: False)

        assert main_module.main(wired["argv"]) == 1
        assert wired["downloaded"] == []

    def test_no_subcommand_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main_module.main([])
        assert exc.value.code == 2

    def test_help_exits_0(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main_module.main(["--help"])
        assert exc.value.code == 0
        # The subcommand's help line, not the `{get}` choices list, which
        # changes whenever a sibling subcommand is added.
        assert "download every track the manifest describes" in capsys.readouterr().out
