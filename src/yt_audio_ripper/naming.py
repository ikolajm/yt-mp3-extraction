import re

# ext4 and most Linux filesystems cap a filename component at 255 bytes.
# Leave headroom for the extension yt-dlp appends.
MAX_STEM_BYTES = 240


def _truncate_bytes(text: str, limit: int) -> str:
    """Cut `text` to at most `limit` UTF-8 bytes without splitting a character."""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def sanitize_filename(name: str) -> str:
    """Reduce a request name to a filename stem safe to join onto a path.

    Any run of characters that is not a letter, digit, underscore, or hyphen
    collapses to a single underscore. This removes path separators and `..`,
    so the result can never escape the output directory. The stem is capped at
    MAX_STEM_BYTES so a long name fails cleanly here rather than as an
    ENAMETOOLONG from yt-dlp. Returns "" if nothing usable is left.
    """
    stem = re.sub(r"[^\w-]+", "_", name, flags=re.UNICODE).strip("_")
    return _truncate_bytes(stem, MAX_STEM_BYTES).strip("_")
