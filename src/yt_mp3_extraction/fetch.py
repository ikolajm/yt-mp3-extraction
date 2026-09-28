from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .config import AUDIO_FORMAT


class FetchError(Exception):
    """Indicate error when fetching."""


def download_mp3(url: str, output_template: Path) -> None:
    """Download the given url"""

    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(output_template),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
                "preferredquality": "5",
            }
        ],
    }

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    except DownloadError as err:
        raise FetchError(str(err)) from err
