from pathlib import Path

import pytest

from huginn.fetch import MediaInfo
from huginn.models import Item, Segment, SourceError
from huginn.pipeline import Options, Pipeline
from huginn.transcriber import Transcript

URL = "https://www.youtube.com/watch?v=abc"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nsubtitle text\n"


class FakeFetcher:
    def __init__(self, manual=(), automatic=(), language="ru", vtt=VTT, error=None):
        self.info = MediaInfo(
            id="abc", title="Talk", url=URL, duration=600, language=language,
            subtitles={k: [] for k in manual}, automatic={k: [] for k in automatic},
        )
        self.vtt = vtt
        self.error = error
        self.tracks = []
        self.audio_dirs = []

    def probe(self, url):
        if self.error:
            raise self.error
        return self.info

    def subtitles(self, info, track):
        self.tracks.append(track)
        return self.vtt

    def audio(self, url, directory):
        self.audio_dirs.append(directory)
        path = directory / "audio.webm"
        path.write_bytes(b"audio")
        return path


class FakeTranscriber:
    label = "Whisper test"

    def __init__(self, segments=(Segment(0, 2, "Recognised text."),), language="ru", error=None):
        self.segments = list(segments)
        self.language = language
        self.error = error
        self.calls = []

    def transcribe(self, audio, language):
        assert Path(audio).exists()
        self.calls.append((Path(audio), language))
        if self.error:
            raise self.error
        return Transcript(self.language, self.segments)


def make(tmp_path, fetcher=None, transcriber=None, ffmpeg=lambda: None, **options):
    fetcher = fetcher or FakeFetcher()
    transcriber = transcriber or FakeTranscriber()
    log = []
    pipeline = Pipeline(Options(out=tmp_path / "out", **options), fetcher, transcriber, log.append, ffmpeg)
    return pipeline, fetcher, transcriber, log


def no_ffmpeg():
    raise SourceError("ffmpeg not found — install it: brew install ffmpeg")


def test_manual_subtitles_are_used_without_recognition(tmp_path):
    pipeline, fetcher, transcriber, _ = make(tmp_path, FakeFetcher(manual=["ru"], automatic=["ru"]), ffmpeg=no_ffmpeg)
    result = pipeline.process(Item("url", URL))
    assert result.status == "created"
    assert not fetcher.tracks[0].automatic
    assert transcriber.calls == [] and fetcher.audio_dirs == []
    text = Path(result.path).read_text()
    assert "- Obtained via: platform subtitles (authored)" in text
    assert "[[00:01]](https://youtu.be/abc?t=1) subtitle text" in text


def test_automatic_subtitles_are_labelled(tmp_path):
    pipeline, _, transcriber, _ = make(tmp_path, FakeFetcher(automatic=["ru", "ru-orig"]))
    result = pipeline.process(Item("url", URL))
    assert transcriber.calls == []
    assert "- Obtained via: platform subtitles (automatic)" in Path(result.path).read_text()


def test_url_without_subtitles_is_recognised_and_audio_removed(tmp_path):
    pipeline, fetcher, transcriber, log = make(tmp_path, FakeFetcher(automatic=["en"]))
    result = pipeline.process(Item("url", URL))
    assert result.status == "created"
    assert len(transcriber.calls) == 1 and transcriber.calls[0][1] is None
    assert not fetcher.audio_dirs[0].exists()
    text = Path(result.path).read_text()
    assert "- Obtained via: Whisper test" in text and "Recognised text." in text
    assert any("speech recognition: Whisper test" in line for line in log)
    assert log[0] == f"→ {URL}"


def test_whisper_flag_ignores_subtitles(tmp_path):
    pipeline, fetcher, transcriber, _ = make(tmp_path, FakeFetcher(manual=["ru"]), whisper=True)
    pipeline.process(Item("url", URL))
    assert fetcher.tracks == [] and len(transcriber.calls) == 1


def test_empty_subtitles_fall_back_to_recognition(tmp_path):
    pipeline, _, transcriber, _ = make(tmp_path, FakeFetcher(manual=["ru"], vtt="WEBVTT\n"))
    assert pipeline.process(Item("url", URL)).status == "created"
    assert len(transcriber.calls) == 1


def test_language_option_is_passed_to_recognition(tmp_path):
    media = tmp_path / "talk.mp4"
    media.touch()
    pipeline, _, transcriber, _ = make(tmp_path, language="en")
    result = pipeline.process(Item("file", str(media)))
    assert transcriber.calls == [(media, "en")]
    assert "- Language: en" in Path(result.path).read_text()


def test_local_file_is_recognised(tmp_path):
    media = tmp_path / "Meine Übung.mp4"
    media.touch()
    pipeline, _, transcriber, _ = make(tmp_path)
    result = pipeline.process(Item("file", str(media)))
    assert result.path == str(tmp_path / "out" / "Meine Übung.md")
    text = Path(result.path).read_text()
    assert text.startswith("# Meine Übung\n")
    assert f"- Source: {media.resolve()}" in text
    assert "[00:00] Recognised text." in text


def test_existing_transcript_is_skipped(tmp_path):
    media = tmp_path / "talk.mp4"
    media.touch()
    pipeline, _, transcriber, _ = make(tmp_path)
    first = pipeline.process(Item("file", str(media)))
    Path(first.path).write_text("user edits")
    second = pipeline.process(Item("file", str(media)))
    assert second.status == "skipped" and second.path == first.path
    assert len(transcriber.calls) == 1
    assert Path(first.path).read_text() == "user edits"


def test_existing_url_transcript_is_skipped_before_download(tmp_path):
    pipeline, fetcher, transcriber, _ = make(tmp_path, FakeFetcher())
    pipeline.process(Item("url", URL))
    assert pipeline.process(Item("url", URL)).status == "skipped"
    assert len(fetcher.audio_dirs) == 1 and len(transcriber.calls) == 1


def test_force_recreates_transcript(tmp_path):
    media = tmp_path / "talk.mp4"
    media.touch()
    pipeline, _, transcriber, _ = make(tmp_path, force=True)
    first = pipeline.process(Item("file", str(media)))
    Path(first.path).write_text("old")
    assert pipeline.process(Item("file", str(media))).status == "created"
    assert "Recognised text." in Path(first.path).read_text()


def test_no_speech_fails_without_file(tmp_path):
    media = tmp_path / "silence.wav"
    media.touch()
    pipeline, _, _, _ = make(tmp_path, transcriber=FakeTranscriber(segments=[Segment(0, 1, "  ")]))
    result = pipeline.process(Item("file", str(media)))
    assert (result.status, result.reason) == ("failed", "no speech found")
    assert not (tmp_path / "out" / "silence.md").exists()


def test_missing_ffmpeg_stops_before_download(tmp_path):
    pipeline, fetcher, transcriber, _ = make(tmp_path, FakeFetcher(), ffmpeg=no_ffmpeg)
    result = pipeline.process(Item("url", URL))
    assert result.status == "failed" and "brew install ffmpeg" in result.reason
    assert fetcher.audio_dirs == [] and transcriber.calls == []


def test_unavailable_url_fails_with_reason(tmp_path):
    pipeline, _, _, _ = make(tmp_path, FakeFetcher(error=SourceError("Video unavailable")))
    result = pipeline.process(Item("url", URL))
    assert (result.status, result.reason) == ("failed", "Video unavailable")


def test_temporary_audio_removed_when_recognition_crashes(tmp_path):
    fetcher = FakeFetcher()
    pipeline, _, _, _ = make(tmp_path, fetcher, FakeTranscriber(error=RuntimeError("boom")))
    result = pipeline.process(Item("url", URL))
    assert (result.status, result.reason) == ("failed", "RuntimeError: boom")
    assert not fetcher.audio_dirs[0].exists()
