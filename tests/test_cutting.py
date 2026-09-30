import subprocess
from pathlib import Path
from typing import Any, NoReturn

import pytest

from yt_mp3_extraction.cutting import CutError, check_times, cut
from yt_mp3_extraction.fetch import source_from_info
from yt_mp3_extraction.models import Track


def slice_track(start: int, end: int | None) -> Track:
    """A sliced track built from its times; the other fields never matter here."""
    return Track(
        path=Path("x.mp3"),
        title="Song",
        artist="Band",
        album="Album",
        track_number=1,
        link="https://link",
        start=start,
        end=end,
    )


class TestCut:
    def test_a_slice_with_an_end_gets_its_duration(
        self,
        ffmpeg_calls: list[list[str]],
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "source.webm"
        target = tmp_path / "out.mp3"

        cut(source, 232, 510, target)

        assert len(ffmpeg_calls) == 1
        command = ffmpeg_calls[0]
        assert command[command.index("-t") + 1] == "278"
        assert command.index("-ss") < command.index("-i")

    def test_a_last_slice_with_no_end_gets_no_duration(
        self,
        ffmpeg_calls: list[list[str]],
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "source.webm"
        target = tmp_path / "out.mp3"

        cut(source, 232, None, target)

        assert len(ffmpeg_calls) == 1
        command = ffmpeg_calls[0]
        assert "-t" not in command

    def test_a_failed_cut_is_a_cut_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "source.webm"
        target = tmp_path / "out.mp3"

        def fake_run(args: list[str], check: bool = False) -> NoReturn:
            raise subprocess.CalledProcessError(1, args)

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(CutError) as exc:
            cut(source, 232, 510, target)

        assert isinstance(exc.value.__cause__, subprocess.CalledProcessError)


class TestCheckTimes:
    def test_a_slice_ending_past_the_video_is_refused(
        self,
        captured_info: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        duration = source_from_info(captured_info, tmp_path).duration
        track = slice_track(0, int(duration) + 1)

        assert len(check_times([track], duration)) == 1

    def test_a_slice_starting_at_the_end_is_refused(
        self,
        captured_info: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        duration = source_from_info(captured_info, tmp_path).duration
        track = slice_track(int(duration), None)

        assert len(check_times([track], duration)) == 1

    def test_a_slice_ending_at_the_end_is_accepted(
        self,
        captured_info: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        duration = source_from_info(captured_info, tmp_path).duration
        track = slice_track(0, int(duration))

        assert check_times([track], duration) == []
