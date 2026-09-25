import subprocess

import pytest

from yt_audio_ripper import check_ffmpeg, check_ytdlp


class TestHasFfmpeg:

    def test_true_when_on_path(self, monkeypatch):
        monkeypatch.setattr(check_ffmpeg.shutil, "which", lambda name: "/usr/bin/ffmpeg")

        assert check_ffmpeg.has_ffmpeg() is True

    def test_false_and_reports_when_absent(self, capsys, monkeypatch):
        monkeypatch.setattr(check_ffmpeg.shutil, "which", lambda name: None)

        assert check_ffmpeg.has_ffmpeg() is False
        assert "ffmpeg" in capsys.readouterr().err


class TestHasYtdlp:

    @pytest.fixture
    def on_path(self, monkeypatch):
        monkeypatch.setattr(check_ytdlp.shutil, "which", lambda name: "/usr/bin/yt-dlp")

    def test_true_when_the_binary_runs(self, monkeypatch, on_path):
        recorded = {}

        def fake_run(command, **kwargs):
            recorded["command"] = command
            recorded["kwargs"] = kwargs
            return subprocess.CompletedProcess(command, 0)

        monkeypatch.setattr(check_ytdlp.subprocess, "run", fake_run)

        assert check_ytdlp.has_ytdlp() is True
        assert recorded["command"] == ["yt-dlp", "--version"]
        # Without check=True a non-zero exit is silent and the error branches
        # below can never fire.
        assert recorded["kwargs"]["check"] is True

    def test_false_and_reports_when_absent(self, capsys, monkeypatch):
        monkeypatch.setattr(check_ytdlp.shutil, "which", lambda name: None)

        assert check_ytdlp.has_ytdlp() is False
        assert "not installed" in capsys.readouterr().err

    @pytest.mark.parametrize("error, expected_fragment", [
        (subprocess.CalledProcessError(2, "yt-dlp", stderr="broken"), "exited 2"),
        (OSError("Exec format error"),                                "Could not execute"),
    ], ids=["exits-nonzero", "not-executable"])
    def test_false_and_reports_when_it_cannot_run(
        self, capsys, monkeypatch, on_path, error, expected_fragment
    ):
        def boom(*a, **k):
            raise error

        monkeypatch.setattr(check_ytdlp.subprocess, "run", boom)

        assert check_ytdlp.has_ytdlp() is False
        assert expected_fragment in capsys.readouterr().err
