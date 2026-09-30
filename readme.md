# yt-mp3-extraction

Downloads the audio from a list of YouTube links and writes one mp3 per row,
sorted into artist and album folders. A row can also be a slice of a longer
video, so one upload of a whole album becomes its tracks. Input is a CSV
manifest, so the files come out named what you called them rather than what the
uploader called them.

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
https://www.youtube.com/watch?v=VIDEO_A,Some Song,Some Band,,,
https://www.youtube.com/watch?v=VIDEO_B,Opener,Other Band,Live EP,,
https://www.youtube.com/watch?v=VIDEO_C,Closer,Other Band,Live EP,,
https://www.youtube.com/watch?v=VIDEO_D,First Track,Third Band,Full Album,0:00,
https://www.youtube.com/watch?v=VIDEO_D,Second Track,Third Band,Full Album,3:52,
https://www.youtube.com/watch?v=VIDEO_D,Last Track,Third Band,Full Album,8:30,
```

`youtube_link`, `title` and `artist` are required columns; `album`, `start` and
`end` are optional and can be left out of the header entirely. A missing
required column, any other column, or a column named twice aborts the run
before anything downloads.

A row without an `album` is a single. Rows sharing an `album` under the same
`artist` are one album, numbered in row order, and may come from several links.
Keep an album's rows together: one split by another row is refused as a likely
paste error. Album names match regardless of case, so `Live EP` and `live ep`
are one album.

Rows sharing a link with a `start` are slices of one video: it downloads once
and is cut into one track per row. If any row for a link has a `start`, every
row for that link needs one, in order. Every slice has an `album`, slices of a
link share one `artist` and one `album`, and an album holding slices holds no
other link. A slice without an `end` runs to the next slice's `start`, or to
the end of the video if it is the last. `start` and `end` are `M:SS` or
`H:MM:SS`, and `end` needs a `start`.

A link can also appear on several rows without times, such as a single that is
also on an album. It downloads once.

Then, from the directory holding `requests.csv`:

```
ytx get
```

`ytx get` reads `./requests.csv` from the directory it runs in. Point it
elsewhere with `--from-file PATH`.

Every row is checked before anything downloads. A row missing a required value,
a malformed time, an `end` without a `start`, more cells than the header has
columns, a broken album or slice rule, or two rows planning to the same file
refuses the whole manifest, and every problem is listed by row. Quote a value
that contains a comma. The file must be UTF-8: from Excel, save it as
"CSV UTF-8", since its plain "CSV" is refused at the first accented character.

A video's length is only known once it downloads, so a slice starting or ending
past it is caught then. Every track of that link fails, nothing is cut, and the
problem is printed; fix the times and rerun.

Exit status is non-zero if the manifest is refused or any track failed.

A single lands at `Artist/Title.mp3` and an album track at
`Artist/Album/NN - Title.mp3`. Track numbers are two digits, widened past 99 so
names still sort. Spaces are kept. Characters Windows or Linux refuses in a
filename (`<>:"/\|?*` and control characters) are removed, whitespace collapses
to single spaces, trailing dots and spaces are stripped, and each part is capped
at 240 bytes. The artist and album folders pass through the same rules, so no
part can escape the output directory or overflow a filesystem limit.

## Output

Files are written to `~/script-output/`, or to `--out DIR`, created if it does
not exist.

Each link is downloaded, converted or cut in a temporary folder inside the
output directory, and each track is moved to its final name only once complete.
A failed or interrupted download or cut leaves nothing under that name, and the
folder is removed. A process killed outright gets no chance to clean up and can
leave a `tmp...` folder behind; delete it.

A track whose file is already there is skipped. A link downloads only if at
least one of its tracks is missing, and then only the missing slices are cut, so
rerunning after a partial failure only fetches what is missing. Delete a file to
force a refetch.

A whole video is converted to mp3 by yt-dlp. A sliced video downloads as the
best audio YouTube serves, and each slice is encoded once, by ffmpeg, at the
same quality.

## Tests

```
pytest
mypy
ruff check
ruff format --check
```

The network and ffmpeg are faked: most tests replace `download_mp3` and
`download_audio`, their own tests replace yt-dlp's `YoutubeDL`, and a fake
ffmpeg records each cut's command instead of running it. The suite covers
manifest parsing, planning, the naming rules, the cut commands, skipping and
the exit codes rather than the download itself.

The code that reads yt-dlp's result is tested against a real one, captured in
`tests/fixtures/me_at_the_zoo.json`. After upgrading yt-dlp, rerun
`python scripts/capture_info.py` (a network call) and read the fixture's diff:
a changed value is drift the tests would otherwise never see.
