from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "requests.csv"
SCRIPT_OUTPUT_DIR = Path.home() / "script-output"

AUDIO_FORMAT = "mp3"
DOWNLOAD_TIMEOUT_SECONDS = 180

EXPECTED_COLUMNS = {"filename", "youtube_link"}
