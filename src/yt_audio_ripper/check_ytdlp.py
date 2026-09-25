import shutil
import subprocess
import sys


def has_ytdlp() -> bool:
    if shutil.which("yt-dlp") is None:
        print("yt-dlp is not installed. Install it to continue.", file=sys.stderr)
        return False
    
    try:
        subprocess.run(
            ["yt-dlp", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as err:
        print(f"yt-dlp found but exited {err.returncode}: {err.stderr.strip()}", file=sys.stderr)
        return False
    except OSError as err:
        print(f"Could not execute yt-dlp: {err}", file=sys.stderr)
        return False