# yt-audio-ripper

Downloads YouTube audio as mp3, one file per row of a `requests.csv` manifest.

Ported from `scripts/youtube-based/yt_link_mp3/` in the hub. This repo is where
a wider media CLI is built out — album and split modes, and an ID3 tagging pass
— so it is laid out as an installable package with an entry point rather than as
a script.

## Install

Python 3.10 or newer. `yt-dlp` and `ffmpeg` are needed as executables on PATH;
neither is a pip package here. Both are resolved with `shutil.which` at startup,
and a missing one exits before the manifest is read.

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows the activate script is `.venv\Scripts\activate`, and that venv puts
`python.exe` in `.venv\Scripts` with no `python3.exe` — so `python3` there falls
through to the system install and reports a dependency missing while it sits
installed in the venv.

The editable install puts `yt_audio_ripper` on the interpreter's path and the
`yt-audio-ripper` command in the venv.

**Check the install landed in the venv.** With the venv unactivated, bare `pip`
on a Linux system resolves to the user-level pip and installs into `~/.local`,
where the tests still pass — against a copy of this package living outside the
venv. `which pip` should print a path under `.venv/bin`.

## Running

From any directory, with the venv active:

```
yt-audio-ripper
```

`python -m yt_audio_ripper.main` does the same thing. The working directory does
not matter: the package is installed, and the manifest is resolved from the
package's own location rather than from the cwd.

Running the file by path fails, and that is expected:

```
$ python src/yt_audio_ripper/main.py
ImportError: attempted relative import with no known parent package
```

A file invoked by path has no parent package, so `from .config import` has
nothing to resolve against. The entry point is what replaces that invocation.

## Manifest

`src/yt_audio_ripper/requests.csv`. The header is exact — an extra or missing
column aborts the run before anything downloads:

```
filename,youtube_link
Some Video Title,https://www.youtube.com/watch?v=VIDEO_ID
```

`filename` is a stem, no extension. Any run of characters outside `[\w-]`
collapses to a single underscore, so the result cannot escape the output
directory, and the stem is capped at 240 bytes to fail here rather than as an
ENAMETOOLONG out of yt-dlp. A row missing either value is skipped and reported;
the rest of the run continues.

The manifest sits inside the package because `CSV_PATH` is resolved from
`__file__`. That is the first thing to change when the CLI takes arguments.

## Output

`~/script-output/`, created if needed. A row whose output file already exists is
skipped without a network call, which makes a rerun after a partial failure
cheap. To force a refetch, delete the file.

Exit is non-zero if any row failed.

## Tests

```
pytest
```

`subprocess.run` is faked, so the tests prove the wiring and the filename rules,
not that yt-dlp runs.

The `src/` layout keeps the source tree off `sys.path`, so the tests import the
installed package rather than the working directory. A packaging mistake — a
module left out of the wheel, a bad `packages.find` — then fails here instead of
passing locally and breaking on a real install.
