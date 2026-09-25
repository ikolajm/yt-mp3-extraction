from dataclasses import dataclass


@dataclass
class RequestRow:
    filename: str
    youtube_link: str