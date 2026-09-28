# yt-mp3-extraction

Downloads the audio from a list of YouTube links and writes one mp3 per link.
Input is a CSV manifest, so the files come out named what you called them rather
than what the uploader called them.

## Requirements

- Python 3.12 or newer
- [ffmpeg](https://ffmpeg.org) on PATH

ffmpeg is an executable, not a pip package. It is checked at startup, and if it
is missing the run exits before anything downloads.
[yt-dlp](https://github.com/yt-dlp/yt-dlp) is a package dependency and installs
with this one, along with deno, the JavaScript runtime it uses for YouTube.

## Install

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows the activate script is `.venv\Scripts\activate`, and that venv has
no `python3.exe` — use `python` there, or `python3` falls through to the system
install.

## Usage

Copy `requests.example.csv` to `requests.csv` and fill it in. `requests.csv` is
gitignored, so your list stays out of the repo. The header is exact; an extra or
missing column aborts the run before anything downloads.

```
filename,youtube_link
Some Video Title,https://www.youtube.com/watch?v=VIDEO_ID
```

Then, from the directory holding `requests.csv`:

```
ytx track
```

`ytx track` reads `./requests.csv` from the directory it runs in. Point it
elsewhere with `--from-file PATH`.

`filename` is a stem, without an extension. Spaces are kept. Characters Windows
or Linux refuses in a filename (`<>:"/\|?*` and control characters) are removed,
whitespace collapses to single spaces, trailing dots and spaces are stripped, and
the stem is capped at 240 bytes, so a name is valid on both systems and cannot
escape the output directory or overflow a filesystem limit.

A row missing either column is reported and skipped; the run continues. Exit
status is non-zero if any row failed.

## Output

Files are written to `~/script-output/`, or to `--out DIR`, created if it does
not exist.

Each file is downloaded and converted in a temporary folder inside the output
directory, and moved to its final name only once complete. A failed or
interrupted download leaves nothing under that name, and the folder is removed.
A process killed outright gets no chance to clean up and can leave a `tmp...`
folder behind; delete it.

A link whose output file is already there is skipped without a network call, so
rerunning after a partial failure only fetches what is missing. Delete a file to
force a refetch.

## Tests

```
pytest
mypy
ruff check
ruff format --check
```

The download is faked: most tests replace `download_mp3`, and its own test
replaces yt-dlp's `YoutubeDL`. The suite covers manifest parsing, the filename
rules and the exit codes rather than the download itself.
