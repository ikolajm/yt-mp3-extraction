from pathlib import Path

import pytest

from yt_mp3_extraction.csv_utilities import ManifestError, read_requests
from yt_mp3_extraction.models import Track
from yt_mp3_extraction.planning import plan_tracks

HEADER = "youtube_link,title,artist,album,start,end\n"

# Planning never touches the disk, so any directory works.
OUT = Path("out")

# The rows of the backlog's Shape example, the same as SHAPE_EXAMPLE in
# test_csv_utilities.py without its header.
SHAPE_BODY = """\
https://youtu.be/AAA,Song One,Some Band,,,
https://youtu.be/BBB,Opener,Other Band,Live EP,,
https://youtu.be/CCC,Closer,Other Band,Live EP,,
https://youtu.be/DDD,Bulls on Parade,RATM,Evil Empire,0:00,
https://youtu.be/DDD,Vietnow,RATM,Evil Empire,3:52,
https://youtu.be/DDD,Revolver,RATM,Evil Empire,8:30,13:05
"""


def plan(tmp_path: Path, body: str) -> list[Track]:
    """Plan a manifest of `body` rows, read the way `ytx get` reads one."""
    path = tmp_path / "requests.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return plan_tracks(read_requests(path), OUT)


class TestPlanTracks:
    def test_an_album_across_links_numbers_in_row_order(self, tmp_path: Path) -> None:
        tracks = plan(
            tmp_path,
            "https://a,Opener,Band,Live EP,,\nhttps://b,Closer,Band,Live EP,,\n",
        )

        assert [track.path for track in tracks] == [
            OUT / "Band" / "Live EP" / "01 - Opener.mp3",
            OUT / "Band" / "Live EP" / "02 - Closer.mp3",
        ]
        assert [track.track_number for track in tracks] == [1, 2]

    def test_album_names_differing_in_case_are_one_album(self, tmp_path: Path) -> None:
        tracks = plan(
            tmp_path,
            "https://a,Opener,Band,Live EP,,\nhttps://b,Closer,Band,live ep,,\n",
        )

        # One folder in the first row's spelling, which Linux would otherwise
        # split in two. Compared as text: WindowsPath ignores case in ==, so
        # comparing Paths passes on Windows either way.
        assert [track.path.as_posix() for track in tracks] == [
            "out/Band/Live EP/01 - Opener.mp3",
            "out/Band/Live EP/02 - Closer.mp3",
        ]

    def test_one_album_name_under_two_artists_is_two_albums(
        self, tmp_path: Path
    ) -> None:
        tracks = plan(
            tmp_path,
            "https://a,Opener,Band A,Live EP,,\nhttps://b,Closer,Band B,Live EP,,\n",
        )

        assert [track.path for track in tracks] == [
            OUT / "Band A" / "Live EP" / "01 - Opener.mp3",
            OUT / "Band B" / "Live EP" / "01 - Closer.mp3",
        ]

    def test_a_single_is_placed_under_its_artist(self, tmp_path: Path) -> None:
        tracks = plan(tmp_path, "https://a,Song,Band,,,\n")

        assert tracks == [
            Track(
                path=OUT / "Band" / "Song.mp3",
                title="Song",
                artist="Band",
                album=None,
                track_number=None,
                link="https://a",
                start=None,
                end=None,
            )
        ]

    def test_an_album_split_by_a_single_is_refused(self, tmp_path: Path) -> None:
        body = (
            "https://a,Opener,Band,Live EP,,\n"
            "https://b,Interlude,Band,,,\n"
            "https://c,Closer,Band,Live EP,,\n"
        )

        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [
            "Row 4: album 'Live EP' by Band continues after other rows; "
            "keep an album's rows together"
        ]

    def test_a_title_with_no_usable_characters_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, "https://a,Song,Band,,,\nhttps://b,...,Band,,,\n")

        assert exc_info.value.problems == [
            "Row 3: title '...' has no usable filename characters"
        ]

    def test_a_link_mixing_slices_and_a_whole_row_is_refused(
        self, tmp_path: Path
    ) -> None:
        """The only slice starts at 0:00, which a truthiness check misses."""
        body = "https://a,One,Band,EP,0:00,\nhttps://a,Two,Band,EP,,\n"

        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [
            "Row 3: this link has slices, so every row for it needs a start"
        ]

    def test_a_slice_without_an_album_is_refused(self, tmp_path: Path) -> None:
        body = "https://a,One,Band,,0:00,\nhttps://a,Two,Band,,3:00,\n"

        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [
            "Row 2: a slice needs an album",
            "Row 3: a slice needs an album",
        ]

    @pytest.mark.parametrize(
        "body",
        [
            "https://a,One,Band,EP,0:00,\nhttps://a,Two,Band,Other EP,3:00,\n",
            "https://a,One,Band,EP,0:00,\nhttps://a,Two,Other Band,EP,3:00,\n",
        ],
        ids=["two albums", "two artists"],
    )
    def test_slices_of_one_link_share_one_album(
        self, tmp_path: Path, body: str
    ) -> None:
        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [
            "Row 2: slices of one link must share one artist and one album"
        ]

    def test_an_album_with_slices_holds_no_other_link(self, tmp_path: Path) -> None:
        body = "https://a,One,Band,EP,0:00,\nhttps://b,Two,Band,EP,,\n"

        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [
            "Row 2: an album with slices holds only that video"
        ]

    def test_one_link_may_be_several_whole_tracks(self, tmp_path: Path) -> None:
        """A single that is also on an album."""
        tracks = plan(tmp_path, "https://a,Song,Band,,,\nhttps://a,Song,Band,EP,,\n")

        assert [track.path.as_posix() for track in tracks] == [
            "out/Band/Song.mp3",
            "out/Band/EP/01 - Song.mp3",
        ]

    def test_plans_the_shape_example(self, tmp_path: Path) -> None:
        """Singles, an album, and one video cut into an album.

        A slice with no end runs to the next slice's start; the last one runs
        to the end of the video, which planning leaves as None.
        """
        tracks = plan(tmp_path, SHAPE_BODY)

        assert tracks == [
            Track(
                path=OUT / "Some Band" / "Song One.mp3",
                title="Song One",
                artist="Some Band",
                album=None,
                track_number=None,
                link="https://youtu.be/AAA",
                start=None,
                end=None,
            ),
            Track(
                path=OUT / "Other Band" / "Live EP" / "01 - Opener.mp3",
                title="Opener",
                artist="Other Band",
                album="Live EP",
                track_number=1,
                link="https://youtu.be/BBB",
                start=None,
                end=None,
            ),
            Track(
                path=OUT / "Other Band" / "Live EP" / "02 - Closer.mp3",
                title="Closer",
                artist="Other Band",
                album="Live EP",
                track_number=2,
                link="https://youtu.be/CCC",
                start=None,
                end=None,
            ),
            Track(
                path=OUT / "RATM" / "Evil Empire" / "01 - Bulls on Parade.mp3",
                title="Bulls on Parade",
                artist="RATM",
                album="Evil Empire",
                track_number=1,
                link="https://youtu.be/DDD",
                start=0,
                end=232,
            ),
            Track(
                path=OUT / "RATM" / "Evil Empire" / "02 - Vietnow.mp3",
                title="Vietnow",
                artist="RATM",
                album="Evil Empire",
                track_number=2,
                link="https://youtu.be/DDD",
                start=232,
                end=510,
            ),
            Track(
                path=OUT / "RATM" / "Evil Empire" / "03 - Revolver.mp3",
                title="Revolver",
                artist="RATM",
                album="Evil Empire",
                track_number=3,
                link="https://youtu.be/DDD",
                start=510,
                end=785,
            ),
        ]

    def test_a_last_slice_with_no_end_runs_to_the_end_of_the_video(
        self, tmp_path: Path
    ) -> None:
        tracks = plan(
            tmp_path, "https://a,One,Band,EP,0:00,\nhttps://a,Two,Band,EP,3:00,\n"
        )

        assert [(track.start, track.end) for track in tracks] == [(0, 180), (180, None)]

    @pytest.mark.parametrize(
        "body, problem",
        [
            (
                "https://a,One,Band,EP,1:00,\nhttps://a,Two,Band,EP,1:00,\n",
                "Row 3: start must be after the previous slice's start",
            ),
            (
                # 0 is falsy, so a truthiness check on the next start skips it.
                "https://a,One,Band,EP,1:00,\nhttps://a,Two,Band,EP,0:00,\n",
                "Row 3: start must be after the previous slice's start",
            ),
            (
                "https://a,One,Band,EP,1:00,1:00\n",
                "Row 2: end must be after start",
            ),
            (
                # 0 is falsy, so a truthiness check on the end skips it.
                "https://a,One,Band,EP,0:00,0:00\n",
                "Row 2: end must be after start",
            ),
            (
                "https://a,One,Band,EP,0:00,2:00\nhttps://a,Two,Band,EP,1:00,\n",
                "Row 2: end passes the next slice's start",
            ),
        ],
        ids=[
            "start repeats",
            "start goes back to 0:00",
            "end equals start",
            "end of 0:00",
            "end passes next start",
        ],
    )
    def test_time_rules_refuse(self, tmp_path: Path, body: str, problem: str) -> None:
        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [problem]

    @pytest.mark.parametrize(
        "body, problem",
        [
            (
                "https://a,Song,Band,,,\nhttps://b,Song,Band,,,\n",
                "Row 3: plans to the same file as row 2: out/Band/Song.mp3",
            ),
            (
                # NTFS treats the two as one file.
                "https://a,Song,Band,,,\nhttps://b,song,Band,,,\n",
                "Row 3: plans to the same file as row 2: out/Band/song.mp3",
            ),
            (
                # The sanitizer strips `?`, leaving the same name.
                "https://a,What?,Band,,,\nhttps://b,What,Band,,,\n",
                "Row 3: plans to the same file as row 2: out/Band/What.mp3",
            ),
        ],
        ids=["same title", "differs in case", "same once sanitized"],
    )
    def test_two_rows_planning_one_file_are_refused(
        self, tmp_path: Path, body: str, problem: str
    ) -> None:
        with pytest.raises(ManifestError) as exc_info:
            plan(tmp_path, body)

        assert exc_info.value.problems == [problem]
