import subprocess

import pytest

from yt_audio_ripper import extraction
from yt_audio_ripper.config import AUDIO_FORMAT
from yt_audio_ripper.models import RequestRow

ROW = RequestRow("Some Song", "https://youtube.com/watch?v=abc")


class TestExtractMp3:

    @pytest.fixture
    def output_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(extraction, "SCRIPT_OUTPUT_DIR", tmp_path)
        return tmp_path

    @pytest.fixture
    def captured(self, monkeypatch):
        """Record the subprocess call. Stays empty if nothing shells out."""
        recorded = {}

        def fake_run(command, **kwargs):
            recorded["command"] = command
            recorded["kwargs"] = kwargs
            return subprocess.CompletedProcess(command, returncode=0)

        monkeypatch.setattr(extraction.subprocess, "run", fake_run)
        return recorded

    def test_builds_the_expected_command(self, captured, output_dir):
        assert extraction.extract_mp3(ROW) is True

        command = captured["command"]
        assert command[0] == "yt-dlp"
        assert "-x" in command
        assert command[command.index("--audio-format") + 1] == AUDIO_FORMAT

        output = command[command.index("-o") + 1]
        assert isinstance(output, str)
        assert output.endswith(".%(ext)s")          # yt-dlp expands this itself
        assert str(output_dir) in output

        assert command[-2:] == ["--", ROW.youtube_link]   # `--` guards a leading dash

    def test_passes_the_configured_timeout(self, captured, output_dir):
        extraction.extract_mp3(ROW)

        assert captured["kwargs"]["timeout"] == extraction.DOWNLOAD_TIMEOUT_SECONDS
        assert captured["kwargs"]["check"] is True

    def test_sanitizes_the_name_before_it_reaches_the_command(self, captured, output_dir):
        extraction.extract_mp3(RequestRow("../../escape attempt", "https://a"))

        output = captured["command"][captured["command"].index("-o") + 1]
        assert "escape_attempt" in output
        assert ".." not in output

    def test_skips_a_file_that_already_exists(self, capsys, captured, output_dir):
        (output_dir / f"Some_Song.{AUDIO_FORMAT}").touch()

        assert extraction.extract_mp3(ROW) is True
        assert "already exists" in capsys.readouterr().out
        assert "command" not in captured

    def test_rejects_a_name_with_nothing_usable_in_it(self, capsys, captured, output_dir):
        assert extraction.extract_mp3(RequestRow("...", "https://a")) is False
        assert "no usable filename" in capsys.readouterr().err
        assert "command" not in captured

    @pytest.mark.parametrize("error, expected_fragment", [
        (subprocess.CalledProcessError(3, "yt-dlp"),        "error code 3"),
        (subprocess.TimeoutExpired("yt-dlp", 180),          "Timed out"),
        (FileNotFoundError(2, "No such file or directory"), "Error running extraction"),
    ], ids=["yt-dlp-exited-nonzero", "yt-dlp-hung", "yt-dlp-vanished"])
    def test_reports_a_failure_without_crashing(
        self, capsys, monkeypatch, output_dir, error, expected_fragment
    ):
        def fake_run(command, **kwargs):
            raise error

        monkeypatch.setattr(extraction.subprocess, "run", fake_run)

        assert extraction.extract_mp3(ROW) is False
        assert expected_fragment in capsys.readouterr().err
