from pathlib import Path
from typing import Any, NoReturn

import pytest

from yt_mp3_extraction import extraction
from yt_mp3_extraction.config import AUDIO_FORMAT
from yt_mp3_extraction.fetch import FetchError
from yt_mp3_extraction.models import RequestRow

ROW = RequestRow("Some Song", "https://youtube.com/watch?v=abc")


class TestExtractMp3:
    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def captured(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
        """Record the seam call. Stays empty if nothing is downloaded."""
        recorded: dict[str, Any] = {}

        def fake_download(url: str, output_template: Path) -> None:
            recorded["url"] = url
            recorded["output_template"] = output_template
            # Leave the file yt-dlp would, so extract_mp3 has one to move.
            Path(str(output_template).replace("%(ext)s", AUDIO_FORMAT)).touch()

        monkeypatch.setattr(extraction, "download_mp3", fake_download)
        return recorded

    def test_hands_the_link_and_template_to_the_seam(
        self, captured: dict[str, Any], output_dir: Path
    ) -> None:
        assert extraction.extract_mp3(ROW, output_dir) is True

        assert captured["url"] == ROW.youtube_link

        template = captured["output_template"]
        assert template.parent.parent == output_dir
        assert template.name.endswith(".%(ext)s")  # yt-dlp expands this itself

    def test_finished_file_ends_up_in_its_place(
        self, captured: dict[str, Any], output_dir: Path
    ) -> None:
        extraction.extract_mp3(ROW, output_dir)

        assert list(output_dir.iterdir()) == [output_dir / f"Some Song.{AUDIO_FORMAT}"]

    def test_sanitizes_the_name_before_it_reaches_the_seam(
        self, captured: dict[str, Any], output_dir: Path
    ) -> None:
        extraction.extract_mp3(
            RequestRow("../../escape attempt", "https://a"), output_dir
        )

        template = captured["output_template"]
        assert template.parent.parent == output_dir
        # The separators are gone; the dots left behind are one harmless name.
        assert template.name == "....escape attempt.%(ext)s"

    def test_skips_a_file_that_already_exists(
        self,
        capsys: pytest.CaptureFixture[str],
        captured: dict[str, Any],
        output_dir: Path,
    ) -> None:
        (output_dir / f"Some Song.{AUDIO_FORMAT}").touch()

        assert extraction.extract_mp3(ROW, output_dir) is True
        assert "already exists" in capsys.readouterr().out
        assert "url" not in captured

    def test_rejects_a_name_with_nothing_usable_in_it(
        self,
        capsys: pytest.CaptureFixture[str],
        captured: dict[str, Any],
        output_dir: Path,
    ) -> None:
        assert (
            extraction.extract_mp3(RequestRow("...", "https://a"), output_dir) is False
        )
        assert "no usable filename" in capsys.readouterr().err
        assert "url" not in captured

    def test_reports_a_failure_without_crashing(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        output_dir: Path,
    ) -> None:
        def fake_download(url: str, output_template: Path) -> NoReturn:
            raise FetchError("boom")

        monkeypatch.setattr(extraction, "download_mp3", fake_download)

        assert extraction.extract_mp3(ROW, output_dir) is False
        assert "Download failed" in capsys.readouterr().err

    def test_an_interrupted_download_leaves_nothing_behind(
        self,
        monkeypatch: pytest.MonkeyPatch,
        output_dir: Path,
    ) -> None:
        def fake_download(url: str, output_template: Path) -> NoReturn:
            Path(str(output_template).replace("%(ext)s", AUDIO_FORMAT)).touch()
            raise KeyboardInterrupt

        monkeypatch.setattr(extraction, "download_mp3", fake_download)

        with pytest.raises(KeyboardInterrupt):
            extraction.extract_mp3(ROW, output_dir)
        assert list(output_dir.iterdir()) == []
