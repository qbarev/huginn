from dataclasses import dataclass, field
from pathlib import Path

from huginn.models import SourceError
from huginn.subtitles import Track

class _Silent:
    """yt-dlp пишет ошибки в stderr сам; причина и так попадает в сводку."""

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


def _reason(error: Exception) -> str:
    return str(error).removeprefix("ERROR: ").strip() or type(error).__name__


class Fetcher:
    """Вся работа с сетью через yt-dlp: метаданные, субтитры, аудиодорожка."""

    def probe(self, url: str) -> MediaInfo:
        import yt_dlp

        try:
            with yt_dlp.YoutubeDL({**_QUIET, "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as error:
            raise SourceError(_reason(error)) from error
        if info.get("_type") == "playlist":
            raise SourceError("плейлисты и каналы не поддерживаются, передайте ссылку на одно видео")
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
        """Возвращает текст дорожки в формате VTT или None, если платформа его не отдаёт."""
        import yt_dlp

        formats = (info.automatic if track.automatic else info.subtitles).get(track.key) or []
        vtt = next((f for f in formats if f.get("ext") == "vtt" and f.get("url")), None)
        if vtt is None:
            return None
        try:
            with yt_dlp.YoutubeDL(_QUIET) as ydl:
                return ydl.urlopen(vtt["url"]).read().decode("utf-8", errors="replace")
        except Exception as error:
            raise SourceError(f"не удалось загрузить субтитры: {_reason(error)}") from error

    def audio(self, url: str, directory: Path) -> Path:
        import yt_dlp

        options = {**_QUIET, "format": "bestaudio/best", "outtmpl": str(directory / "audio.%(ext)s")}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                return Path(ydl.prepare_filename(info))
        except yt_dlp.utils.DownloadError as error:
            raise SourceError(_reason(error)) from error
