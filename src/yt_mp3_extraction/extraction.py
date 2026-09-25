from pathlib import Path
import subprocess
import sys

from .naming import sanitize_filename
from .config import AUDIO_FORMAT
from .models import RequestRow


def extract_mp3(row: RequestRow, out_dir: Path, timeout: int) -> bool:
    """Download one request's audio into out_dir.

    Returns True on success or if the file is already present, False if the
    name is unusable or yt-dlp failed.
    """
    file_stem = sanitize_filename(row.filename)
    if not file_stem:
        print(f"Skipping {row.filename!r}: no usable filename characters.", file=sys.stderr)
        return False

    final_path = out_dir / f"{file_stem}.{AUDIO_FORMAT}"
    if final_path.exists():
        print(f"Skipping {row.filename!r}: {final_path.name} already exists.")
        return True

    # yt-dlp fills in %(ext)s itself; the extension changes between download
    # and audio extraction.
    output_template = out_dir / f"{file_stem}.%(ext)s"
    command = [
        "yt-dlp",
        "-x",
        "--audio-format", AUDIO_FORMAT,
        "-o", str(output_template),
        "--",  # End of yt-dlp options
        row.youtube_link,
    ]

    try:
        subprocess.run(command, check=True, timeout=timeout)
        print(f"Download complete: {final_path.name}")
        return True
    except subprocess.TimeoutExpired as err:
        print(f"Timed out after {err.timeout} seconds: {row.filename}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as err:
        print(f"Download failed, yt-dlp exited with error code {err.returncode}: "
              f"{row.filename}", file=sys.stderr)
        return False
    except OSError as err:
        print(f"Error running extraction for `{row.filename}`: {err}", file=sys.stderr)
        return False
