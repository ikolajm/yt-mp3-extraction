from pathlib import Path
from typing import Any

import pytest

from yt_mp3_extraction import main as main_module
from yt_mp3_extraction.models import Track

HEADER = "youtube_link,title,artist\n"
ALBUM_HEADER = "youtube_link,title,artist,album\n"


class TestMain:
    @pytest.fixture
    def wired(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
        """Sandbox main(): deps present, paths in tmp_path, no downloads.

        The fake fails any track named FAIL*.
        """
        csv_path = tmp_path / "requests.csv"
        output_dir = tmp_path / "out"
        downloaded: list[list[Track]] = []
        seen: dict[str, Any] = {}

        def fake_extract_link(tracks: list[Track], out_dir: Path) -> int:
            downloaded.append(tracks)
            seen["out_dir"] = out_dir
            return sum(1 for t in tracks if t.title.startswith("FAIL"))

        monkeypatch.setattr(main_module, "has_ffmpeg", lambda: True)
        monkeypatch.setattr(main_module, "extract_link", fake_extract_link)

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
        # One call per link, each holding that link's tracks.
        assert [[t.title for t in call] for call in wired["downloaded"]] == [
            ["Song One"],
            ["Song Two"],
        ]
        assert wired["seen"]["out_dir"] == wired["output_dir"]
        assert wired["output_dir"].is_dir()

    def test_any_failure_exits_1(
        self, capsys: pytest.CaptureFixture[str], wired: dict[str, Any]
    ) -> None:
        wired["csv"].write_text(
            HEADER + "https://a,OK,Some Band\nhttps://b,FAIL Two,Some Band\n"
        )

        assert main_module.main(wired["argv"]) == 1
        assert "1/2 tracks in place" in capsys.readouterr().out

    def test_rows_sharing_a_link_reach_extraction_together(
        self, wired: dict[str, Any]
    ) -> None:
        # A single that is also on an album: one link, two tracks, one call.
        wired["csv"].write_text(
            ALBUM_HEADER
            + "https://a,Song One,Some Band,\n"
            + "https://a,Song One,Some Band,Live EP\n"
        )

        assert main_module.main(wired["argv"]) == 0
        assert len(wired["downloaded"]) == 1
        assert len(wired["downloaded"][0]) == 2

    def test_a_plan_refusal_is_reported_and_creates_nothing(
        self, capsys: pytest.CaptureFixture[str], wired: dict[str, Any]
    ) -> None:
        """Ordering: plan before creating anything on disk."""
        # Each row reads fine; the planner refuses album X split by a single.
        wired["csv"].write_text(
            ALBUM_HEADER
            + "https://a,One,Band,X\n"
            + "https://b,Two,Band,\n"
            + "https://c,Three,Band,X\n"
        )

        assert main_module.main(wired["argv"]) == 1
        assert not wired["output_dir"].exists()
        assert wired["downloaded"] == []
        assert "keep an album's rows together" in capsys.readouterr().err

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
