from dataclasses import dataclass


@dataclass
class RequestRow:
    youtube_link: str
    title: str
    artist: str
    album: str | None = None
    start: int | None = None
    end: int | None = None
