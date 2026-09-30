"""Save the yt-dlp fields the code reads, for one video, as the tests' fixture.

Rerun after upgrading yt-dlp and read the fixture's diff: a changed value is
drift the tests would otherwise never see.
"""

import json
from pathlib import Path

from yt_dlp import YoutubeDL

from yt_mp3_extraction.config import DOWNLOAD_FORMAT

URL: str = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
KEEP: tuple[str, ...] = ("id", "title", "duration", "ext")
OUT: Path = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "me_at_the_zoo.json"
)


def main() -> None:
    options = {"format": DOWNLOAD_FORMAT, "noplaylist": True}

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(URL, download=False)
        sanitized_info = ydl.sanitize_info(info)
        kept_info = {key: sanitized_info[key] for key in KEEP}

        text = json.dumps(kept_info, indent=2) + "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")

    print(f"JSON written to: {OUT}")


if __name__ == "__main__":
    main()
