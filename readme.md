# yt-mp3-extraction

Downloads the audio from a list of YouTube links and writes one mp3 per row.
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
gitignored, so your list stays out of the repo.

```
youtube_link,title,artist,album,start,end
https://www.youtube.com/watch?v=VIDEO_ID,Some Song,Some Band,,,
https://www.youtube.com/watch?v=VIDEO_ID,Opener,Other Band,Live EP,,
```

`youtube_link`, `title` and `artist` are required columns; `album`, `start` and
`end` are optional and can be left out of the header entirely. A missing
required column, any other column, or a column named twice aborts the run
before anything downloads.

`album`, `start` and `end` are read and checked but not yet acted on: every row
downloads its whole video as one file. `start` and `end` are `M:SS` or
`H:MM:SS`, and `end` needs a `start`.

Then, from the directory holding `requests.csv`:

```
ytx get
```

`ytx get` reads `./requests.csv` from the directory it runs in. Point it
elsewhere with `--from-file PATH`.

Every row is checked before anything downloads. A row missing a required value,
a malformed time, an `end` without a `start` or more cells than the header has
columns refuses the whole manifest, and every problem is listed by row. Quote a
value that contains a comma. Exit status is non-zero if the manifest is refused
or any row failed.

Each file is named from its `title`. Spaces are kept. Characters Windows or
Linux refuses in a filename (`<>:"/\|?*` and control characters) are removed,
whitespace collapses to single spaces, trailing dots and spaces are stripped,
and the name is capped at 240 bytes, so it is valid on both systems and cannot
escape the output directory or overflow a filesystem limit.

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
replaces yt-dlp's `YoutubeDL`. The suite covers manifest parsing, the naming
rules and the exit codes rather than the download itself.
