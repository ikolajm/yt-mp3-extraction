from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .config import AUDIO_FORMAT, AUDIO_QUALITY, DOWNLOAD_FORMAT
from .models import Source


class FetchError(Exception):
    """Indicate error when fetching."""


SOURCE_STEM = "source"


def source_from_info(info: dict[str, Any], staging_dir: Path) -> Source:
    """Turns yt-dlp's info dict into the typed Source for a staged download."""

    path = staging_dir / f"{SOURCE_STEM}.{info['ext']}"
    duration = info.get("duration")

    if duration is None:
        raise FetchError(
            "the video reports no duration; live streams and premieres have none"
        )

    return Source(path=path, duration=float(duration))


def download_mp3(url: str, output_template: Path) -> None:
    """Download the given url."""

    options: dict[str, Any] = {
        "format": DOWNLOAD_FORMAT,
        "outtmpl": str(output_template),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
                "preferredquality": AUDIO_QUALITY,
            }
        ],
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    except DownloadError as err:
        raise FetchError(str(err)) from err


def download_audio(url: str, staging_dir: Path) -> Source:
    """Download the url's best audio into staging_dir, unconverted, for cutting."""

    options: dict[str, Any] = {
        "format": DOWNLOAD_FORMAT,
        "outtmpl": str(staging_dir / f"{SOURCE_STEM}.%(ext)s"),
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url)
    except DownloadError as err:
        raise FetchError(str(err)) from err

    return source_from_info(info, staging_dir)
