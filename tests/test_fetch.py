import sys
import types

import pytest

from huginn.fetch import Fetcher
from huginn.models import SourceError
from huginn.subtitles import Track


class DownloadError(Exception):
    pass


@pytest.fixture
def ydl(monkeypatch):
    """Подменяет модуль yt_dlp; возвращает объект для настройки ответов и чтения вызовов."""
    state = types.SimpleNamespace(info={}, error=None, body=b"", calls=[])

    class YoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            state.calls.append(("extract_info", url, download, self.options))
            if state.error:
                raise state.error
            return state.info

        def prepare_filename(self, info):
            return self.options["outtmpl"].replace("%(ext)s", info["ext"])

        def urlopen(self, url):
            state.calls.append(("urlopen", url))
            return types.SimpleNamespace(read=lambda: state.body)

    module = types.ModuleType("yt_dlp")
    module.YoutubeDL = YoutubeDL
    module.utils = types.SimpleNamespace(DownloadError=DownloadError)
    monkeypatch.setitem(sys.modules, "yt_dlp", module)
    return state


def test_probe_maps_metadata(ydl):
    ydl.info = {
        "id": "abc", "title": "Доклад", "duration": 600, "language": "ru",
        "subtitles": {"ru": [{"ext": "vtt", "url": "u"}]}, "automatic_captions": {"ru-orig": []},
    }
    info = Fetcher().probe("https://example.com/v")
    assert (info.id, info.title, info.url, info.duration, info.language) == (
        "abc", "Доклад", "https://example.com/v", 600, "ru")
    assert list(info.subtitles) == ["ru"] and list(info.automatic) == ["ru-orig"]
    _, url, download, options = ydl.calls[0]
    assert (url, download) == ("https://example.com/v", False)
    assert options["skip_download"] and options["noplaylist"]


def test_probe_rejects_playlists(ydl):
    ydl.info = {"_type": "playlist", "id": "PL1"}
    with pytest.raises(SourceError, match="плейлисты"):
        Fetcher().probe("https://example.com/list")


def test_download_error_becomes_source_error(ydl):
    ydl.error = DownloadError("ERROR: Video unavailable")
    with pytest.raises(SourceError, match="^Video unavailable$"):
        Fetcher().probe("https://example.com/v")
    with pytest.raises(SourceError, match="^Video unavailable$"):
        Fetcher().audio("https://example.com/v", __import__("pathlib").Path("/tmp/x"))


def test_subtitles_downloads_vtt_of_chosen_track(ydl):
    ydl.info = {
        "id": "abc", "title": "t",
        "subtitles": {"ru": [{"ext": "json3", "url": "j"}, {"ext": "vtt", "url": "manual-vtt"}]},
        "automatic_captions": {"ru-orig": [{"ext": "vtt", "url": "auto-vtt"}], "en": [{"ext": "srt", "url": "s"}]},
    }
    ydl.body = "WEBVTT\n".encode()
    fetcher = Fetcher()
    info = fetcher.probe("https://example.com/v")
    assert fetcher.subtitles(info, Track("ru", automatic=False)) == "WEBVTT\n"
    assert fetcher.subtitles(info, Track("ru-orig", automatic=True)) == "WEBVTT\n"
    assert [c[1] for c in ydl.calls if c[0] == "urlopen"] == ["manual-vtt", "auto-vtt"]
    assert fetcher.subtitles(info, Track("en", automatic=True)) is None


def test_audio_downloads_best_audio_into_directory(ydl, tmp_path):
    ydl.info = {"id": "abc", "ext": "webm"}
    path = Fetcher().audio("https://example.com/v", tmp_path)
    assert path == tmp_path / "audio.webm"
    _, url, download, options = ydl.calls[0]
    assert (url, download, options["format"]) == ("https://example.com/v", True, "bestaudio/best")
