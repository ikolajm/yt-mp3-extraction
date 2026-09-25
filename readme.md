# yt-mp3-extraction

Downloads the audio from a list of YouTube links and writes one mp3 per link.
Input is a CSV manifest, so the files come out named what you called them rather
than what the uploader called them.

## Requirements

- Python 3.10 or newer
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org)
  on PATH

Those two are executables, not pip packages. Both are checked at startup, and a
missing one exits before anything downloads.

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

`filename` is a stem, without an extension. Any run of characters outside
`[\w-]` collapses to a single underscore, and the stem is capped at 240 bytes,
so a name cannot escape the output directory or overflow a filesystem limit.

A row missing either column is reported and skipped; the run continues. Exit
status is non-zero if any row failed.

## Output

Files are written to `~/script-output/`, or to `--out DIR`, created if it does
not exist. Each download is abandoned after 180 seconds; `--timeout SECONDS`
changes that.

A link whose output file is already there is skipped without a network call, so
rerunning after a partial failure only fetches what is missing. Delete a file to
force a refetch.

## Tests

```
pytest
```

`subprocess.run` is faked, so the suite covers manifest parsing, the filename
rules and the exit codes rather than the download itself.
