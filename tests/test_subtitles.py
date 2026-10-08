from pathlib import Path

from huginn.models import Segment
from huginn.subtitles import Track, choose_track, parse_vtt

DATA = Path(__file__).parent / "data"


def test_manual_subtitles_lose_markup():
    segments = parse_vtt((DATA / "manual.vtt").read_text())
    assert segments == [
        Segment(1.0, 3.5, "Hello & welcome, everyone."),
        Segment(3734.25, 3736.0, "Thanks for watching."),
    ]


def test_youtube_auto_subtitles_lose_rolling_repeats():
    segments = parse_vtt((DATA / "youtube_auto.vtt").read_text())
    assert [s.text for s in segments] == [
        "[applause]",
        "good afternoon so i always try",
        "to build our meeting so it isn't",
        "some tedious lecture with a",
        "set",
    ]
    assert segments[0].start == 2.92
    assert segments[1].start == 5.06
    assert segments[1].end == 8.6


def test_crlf_and_empty_input():
    assert parse_vtt("WEBVTT\r\n\r\n00:01.000 --> 00:02.000\r\nhi\r\n") == [Segment(1.0, 2.0, "hi")]
    assert parse_vtt("WEBVTT\n") == []


def test_manual_track_preferred_over_automatic():
    assert choose_track(["ru", "en"], ["ru", "ru-orig"], None, "ru") == Track("ru", automatic=False)


def test_automatic_track_prefers_original():
    assert choose_track([], ["en", "ru", "ru-orig"], None, "ru") == Track("ru-orig", automatic=True)
    assert choose_track(["live_chat"], ["en", "en-US"], None, "en-US") == Track("en", automatic=True)


def test_requested_language_wins_and_matches_regional_keys():
    assert choose_track(["en-GB", "ru"], [], "en", "ru") == Track("en-GB", automatic=False)


def test_unknown_language_takes_the_only_manual_track():
    assert choose_track(["de"], ["en", "ru"], None, None) == Track("de", automatic=False)
    assert choose_track(["de", "fr"], ["en"], None, None) is None
    assert choose_track([], ["en", "ru"], None, None) is None


def test_no_track_in_media_language():
    assert choose_track(["en"], ["en"], None, "ru") is None
