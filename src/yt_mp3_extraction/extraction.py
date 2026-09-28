import sys
import tempfile
from pathlib import Path

from .config import AUDIO_FORMAT
from .fetch import FetchError, download_mp3
from .models import RequestRow
from .naming import sanitize_filename


def extract_mp3(row: RequestRow, out_dir: Path) -> bool:
    """Download one request's audio into out_dir.

    Returns True on success or if the file is already present, False if the
    name is unusable or yt-dlp failed.
    """
    file_stem = sanitize_filename(row.filename)
    if not file_stem:
        print(
            f"Skipping {row.filename!r}: no usable filename characters.",
            file=sys.stderr,
        )
        return False

    final_path = out_dir / f"{file_stem}.{AUDIO_FORMAT}"
    if final_path.exists():
        print(f"Skipping {row.filename!r}: {final_path.name} already exists.")
        return True

    # Download into a staging directory and move the finished file into place,
    # so an interrupted conversion never leaves a partial file under the final
    # name for skip-if-exists to trust. Staging sits inside out_dir so the move
    # is a rename on one filesystem.
    with tempfile.TemporaryDirectory(dir=out_dir) as staging:
        staging_dir = Path(staging)

        # yt-dlp fills in %(ext)s itself; the extension changes between
        # download and audio extraction.
        output_template = staging_dir / f"{file_stem}.%(ext)s"

        try:
            download_mp3(row.youtube_link, output_template)
            # replace, not rename: rename refuses an existing target on Windows.
            (staging_dir / final_path.name).replace(final_path)
            print(f"Download complete: {final_path.name}")
            return True
        except FetchError:
            print(f"Download failed: {row.filename}", file=sys.stderr)
            return False
