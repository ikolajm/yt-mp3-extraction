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


class TestDownloadMp3:
    def test_turns_a_download_error_into_a_fetch_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # fetch.py imported the name, so the fake goes on fetch, not on yt_dlp.
        monkeypatch.setattr(fetch, "YoutubeDL", FakeYoutubeDL)

        with pytest.raises(fetch.FetchError) as exc:
            fetch.download_mp3("https://a", tmp_path / "song.%(ext)s")

        assert isinstance(exc.value.__cause__, DownloadError)
