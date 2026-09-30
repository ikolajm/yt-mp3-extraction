import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

# One video's yt-dlp result, trimmed to the keys the code reads. Rerun
# scripts/capture_info.py after a yt-dlp upgrade and read the diff.
FIXTURE = Path(__file__).parent / "fixtures" / "me_at_the_zoo.json"


@pytest.fixture
def captured_info() -> dict[str, Any]:
    """The captured yt-dlp result, loaded fresh for each test that asks."""
    info: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return info


@pytest.fixture
def ffmpeg_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Returns the list of recorded commands. Stays empty if nothing is cut."""

    calls: list[list[str]] = []

    def fake_run(
        args: list[str], check: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        Path(args[-1]).touch()
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls
