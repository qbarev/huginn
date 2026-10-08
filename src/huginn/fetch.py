from dataclasses import dataclass, field
from pathlib import Path

from huginn.models import SourceError
from huginn.subtitles import Track

class _Silent:
    """yt-dlp prints errors to stderr itself; the reason already goes into the summary."""

    def debug(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


_QUIET = {"quiet": True, "no_warnings": True, "noplaylist": True, "noprogress": True, "logger": _Silent()}


@dataclass(frozen=True)
class MediaInfo:
    id: str
    title: str
    url: str
    duration: float | None
    language: str | None
    subtitles: dict[str, list[dict]] = field(default_factory=dict)
    automatic: dict[str, list[dict]] = field(default_factory=dict)


@dataclass(frozen=True)
class Entry:
    url: str
    id: str | None = None


@dataclass(frozen=True)
class Playlist:
    id: str
    title: str
    entries: list[Entry]


def _reason(error: Exception) -> str:
    return str(error).removeprefix("ERROR: ").strip() or type(error).__name__


def _playlist(info: dict) -> Playlist:
    playlist_id = str(info.get("id") or "")
    if playlist_id and playlist_id == info.get("channel_id"):
        raise SourceError("channels are not supported, pass a link to a playlist")
    entries = [
        Entry(link, str(entry["id"]) if entry.get("id") else None)
        for entry in info.get("entries") or []
        if entry and (link := entry.get("url") or entry.get("webpage_url"))
    ]
    return Playlist(playlist_id, info.get("title") or playlist_id, entries)


class Fetcher:
    """All network access through yt-dlp: metadata, subtitles, audio track."""

    def probe(self, url: str) -> MediaInfo | Playlist:
        """Metadata of the media behind the link, or the list of videos if the link is a playlist."""
        import yt_dlp

        options = {**_QUIET, "skip_download": True, "extract_flat": "in_playlist"}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get("_type") == "playlist":
                    return _playlist(info)
        except yt_dlp.utils.DownloadError as error:
            raise SourceError(_reason(error)) from error
        return MediaInfo(
            id=str(info.get("id") or ""),
            title=info.get("title") or str(info.get("id") or url),
            url=url,
            duration=info.get("duration"),
            language=info.get("language"),
            subtitles=info.get("subtitles") or {},
            automatic=info.get("automatic_captions") or {},
        )

    def subtitles(self, info: MediaInfo, track: Track) -> str | None:
        """Return the track as VTT text, or None if the platform does not offer VTT."""
        import yt_dlp

        formats = (info.automatic if track.automatic else info.subtitles).get(track.key) or []
        vtt = next((f for f in formats if f.get("ext") == "vtt" and f.get("url")), None)
        if vtt is None:
            return None
        try:
            with yt_dlp.YoutubeDL(_QUIET) as ydl:
                return ydl.urlopen(vtt["url"]).read().decode("utf-8", errors="replace")
        except Exception as error:
            raise SourceError(f"could not download subtitles: {_reason(error)}") from error

    def audio(self, url: str, directory: Path) -> Path:
        import yt_dlp

        options = {**_QUIET, "format": "bestaudio/best", "outtmpl": str(directory / "audio.%(ext)s")}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                return Path(ydl.prepare_filename(info))
        except yt_dlp.utils.DownloadError as error:
            raise SourceError(_reason(error)) from error
