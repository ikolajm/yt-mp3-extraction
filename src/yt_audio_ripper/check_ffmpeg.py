import shutil
import sys

def has_ffmpeg() -> bool:
    if shutil.which("ffmpeg") is None:
        print("`ffmpeg` required for options this script depends on (`--audio-format mp3`). Please install to continue.", file=sys.stderr)
        return False
    else:
        return True