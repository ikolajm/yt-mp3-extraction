from pathlib import Path
from typing import Any, NoReturn, Self

import pytest
from yt_dlp.utils import DownloadError

from yt_mp3_extraction import fetch


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL; every download fails."""

    def __init__(self, options: dict[str, Any]) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Returning None lets the exception keep propagating; True would
        # swallow it.
        pass

    def download(self, urls: list[str]) -> NoReturn:
        raise DownloadError("boom")

    def extract_info(self, url: str, download: bool = True) -> NoReturn:
        raise DownloadError("boom")


class TestSourceFromInfo:
    def test_reads_the_captured_video(
        self,
        captured_info: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        source = fetch.source_from_info(captured_info, tmp_path)

        # The captured values, written out: a rerun of the capture that
        # changes either one turns this red.
        assert source.duration == 19
        assert source.path == tmp_path / "source.webm"

    def test_a_video_without_a_duration_is_a_fetch_error(
        self,
        captured_info: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        # Live streams and premieres report none.
        info = {**captured_info, "duration": None}

        with pytest.raises(fetch.FetchError):
            fetch.source_from_info(info, tmp_path)


class TestDownloadMp3:
    def test_turns_a_download_error_into_a_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # fetch.py imported the name, so the fake goes on fetch, not on yt_dlp.
        monkeypatch.setattr(fetch, "YoutubeDL", FakeYoutubeDL)

        with pytest.raises(fetch.FetchError) as exc:
            fetch.download_mp3("https://a", tmp_path / "song.%(ext)s")

        assert isinstance(exc.value.__cause__, DownloadError)


class TestDownloadAudio:
    def test_turns_a_download_error_into_a_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(fetch, "YoutubeDL", FakeYoutubeDL)

        with pytest.raises(fetch.FetchError) as exc:
            fetch.download_audio("https://a", tmp_path)

        assert isinstance(exc.value.__cause__, DownloadError)
