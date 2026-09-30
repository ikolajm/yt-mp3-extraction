from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RequestRow:
    youtube_link: str
    title: str
    artist: str
    album: str | None = None
    start: int | None = None
    end: int | None = None
    line: int = field(kw_only=True)


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str
    album: str | None
    track_number: int | None
    link: str
    start: int | None
    end: int | None


@dataclass(frozen=True)
class Source:
    path: Path
    duration: float
