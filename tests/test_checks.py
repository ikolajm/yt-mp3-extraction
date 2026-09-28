import shutil

import pytest

from yt_mp3_extraction import check_ffmpeg


class TestHasFfmpeg:
    def test_true_when_on_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/ffmpeg")

        assert check_ffmpeg.has_ffmpeg() is True

    def test_false_and_reports_when_absent(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(shutil, "which", lambda name: None)

        assert check_ffmpeg.has_ffmpeg() is False
        assert "ffmpeg" in capsys.readouterr().err
