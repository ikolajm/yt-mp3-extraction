import subprocess
from dataclasses import replace
from pathlib import Path
from typing import NoReturn

import pytest

from yt_mp3_extraction import extraction
from yt_mp3_extraction.config import AUDIO_FORMAT
from yt_mp3_extraction.fetch import FetchError
from yt_mp3_extraction.models import RequestRow, Source
from yt_mp3_extraction.planning import plan_tracks

ROW = RequestRow("https://youtube.com/watch?v=abc", "Some Song", "Some Band", line=2)
SLICES = [
    RequestRow(
        "https://shared_link", "Bulls on Parade", "RATM", "Evil Empire", 0, line=2
    ),
    RequestRow("https://shared_link", "Vietnow", "RATM", "Evil Empire", 232, line=3),
    RequestRow("https://shared_link", "Revolver", "RATM", "Evil Empire", 510, line=4),
]
SINGLE = [ROW]


class TestExtractLink:
    @pytest.fixture
    def downloads(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        urls: list[str] = []

        def fake_download(url: str, output_template: Path) -> None:
            urls.append(url)
            # Leave source.mp3 where yt-dlp would;
            # extract_link copies each track from it.
            Path(str(output_template).replace("%(ext)s", AUDIO_FORMAT)).touch()

        def fake_download_audio(url: str, staging_dir: Path) -> Source:
            urls.append(url)
            audio = staging_dir / "source.webm"
            audio.touch()
            return Source(audio, 600.0)

        monkeypatch.setattr(extraction, "download_mp3", fake_download)
        monkeypatch.setattr(extraction, "download_audio", fake_download_audio)

        return urls

    def test_a_whole_video_lands_at_its_layout_path(
        self, downloads: list[str], tmp_path: Path
    ) -> None:
        tracks = plan_tracks(SINGLE, tmp_path)

        assert extraction.extract_link(tracks, tmp_path) == 0
        assert list(tmp_path.iterdir()) == [tmp_path / "Some Band"]
        assert (tmp_path / "Some Band" / "Some Song.mp3").exists()

    def test_a_link_on_two_rows_downloads_once(
        self, downloads: list[str], tmp_path: Path
    ) -> None:
        rows = [
            RequestRow("https://shared_link", "Bulls on Parade", "RATM", line=2),
            RequestRow(
                "https://shared_link", "Bulls on Parade", "RATM", "Evil Empire", line=3
            ),
        ]

        tracks = plan_tracks(rows, tmp_path)

        assert extraction.extract_link(tracks, tmp_path) == 0
        assert downloads == ["https://shared_link"]
        assert (tmp_path / "RATM" / "Bulls on Parade.mp3").exists()
        assert (tmp_path / "RATM" / "Evil Empire" / "01 - Bulls on Parade.mp3").exists()

    def test_a_sliced_link_cuts_one_track_per_slice(
        self, downloads: list[str], ffmpeg_calls: list[list[str]], tmp_path: Path
    ) -> None:
        tracks = plan_tracks(SLICES, tmp_path)
        album = tmp_path / "RATM" / "Evil Empire"

        assert extraction.extract_link(tracks, tmp_path) == 0
        assert downloads == ["https://shared_link"]
        assert len(ffmpeg_calls) == 3
        assert sorted(p.name for p in album.iterdir())

    def test_a_link_whose_tracks_all_exist_is_not_downloaded(
        self, downloads: list[str], ffmpeg_calls: list[list[str]], tmp_path: Path
    ) -> None:
        tracks = plan_tracks(SLICES, tmp_path)

        for track in tracks:
            track.path.parent.mkdir(parents=True, exist_ok=True)
            track.path.touch()

        assert extraction.extract_link(tracks, tmp_path) == 0
        assert downloads == []
        assert ffmpeg_calls == []

    def test_only_missing_slices_are_cut(
        self, downloads: list[str], ffmpeg_calls: list[list[str]], tmp_path: Path
    ) -> None:
        tracks = plan_tracks(SLICES, tmp_path)

        tracks[1].path.parent.mkdir(parents=True, exist_ok=True)
        tracks[1].path.touch()

        assert extraction.extract_link(tracks, tmp_path) == 0
        assert downloads == ["https://shared_link"]
        assert len(ffmpeg_calls) == 2

    def test_a_time_past_the_duration_cuts_nothing(
        self,
        capsys: pytest.CaptureFixture[str],
        downloads: list[str],
        ffmpeg_calls: list[list[str]],
        tmp_path: Path,
    ) -> None:
        rows = SLICES[:2] + [replace(SLICES[2], end=785)]
        tracks = plan_tracks(rows, tmp_path)

        assert extraction.extract_link(tracks, tmp_path) == 3
        assert ffmpeg_calls == []
        assert "785" in capsys.readouterr().err

    def test_a_failed_download_fails_every_pending_track(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        downloads: list[str],
        ffmpeg_calls: list[list[str]],
        tmp_path: Path,
    ) -> None:
        def broken(url: str, staging_dir: Path) -> NoReturn:
            raise FetchError("unavailable")

        monkeypatch.setattr(extraction, "download_audio", broken)

        tracks = plan_tracks(SLICES, tmp_path)

        assert extraction.extract_link(tracks, tmp_path) == 3
        assert ffmpeg_calls == []
        assert "unavailable" in capsys.readouterr().err

    def test_an_interrupted_cut_leaves_nothing_behind(
        self, downloads: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def interrupted_run(args: list[str], check: bool = False) -> NoReturn:
            # ffmpeg has written part of its output when Ctrl+C lands.
            Path(args[-1]).touch()
            raise KeyboardInterrupt

        monkeypatch.setattr(subprocess, "run", interrupted_run)
        tracks = plan_tracks(SLICES, tmp_path)

        with pytest.raises(KeyboardInterrupt):
            extraction.extract_link(tracks, tmp_path)
        # Staging is gone with the partial file, and nothing was placed.
        assert list(tmp_path.iterdir()) == []
