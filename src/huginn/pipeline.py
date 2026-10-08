import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from huginn import subtitles
from huginn.fetch import Entry, Fetcher, MediaInfo, Playlist
from huginn.models import Item, Result, Segment, SourceError
from huginn.render import Meta, id_suffix, numbered_name, output_name, playlist_dir_name, render
from huginn.transcriber import Transcriber, require_ffmpeg


@dataclass(frozen=True)
class Options:
    out: Path = Path("transcripts")
    whisper: bool = False
    language: str | None = None
    force: bool = False


def _transcript_of(directory: Path, media_id: str | None) -> Path | None:
    if not media_id or not directory.is_dir():
        return None
    suffix = id_suffix(media_id)
    return next((p for p in sorted(directory.iterdir()) if p.name.endswith(suffix)), None)


class Pipeline:
    def __init__(
        self,
        options: Options,
        fetcher: Fetcher,
        transcriber: Transcriber,
        log: Callable[[str], None] = lambda message: None,
        check_ffmpeg: Callable[[], None] = require_ffmpeg,
    ):
        self.options = options
        self.fetcher = fetcher
        self.transcriber = transcriber
        self.log = log
        self.check_ffmpeg = check_ffmpeg

    def process(self, item: Item) -> list[Result]:
        """Process one source; any error becomes a result, not an exception."""
        self.log(f"→ {item.value}")
        if item.kind == "url":
            return self._guarded(item.value, lambda: self._link(item.value))
        return self._guarded(item.value, lambda: [self._file(Path(item.value))])

    def _guarded(self, source: str, action: Callable[[], list[Result]]) -> list[Result]:
        try:
            return action()
        except SourceError as error:
            return [Result(source, "failed", reason=str(error))]
        except Exception as error:
            return [Result(source, "failed", reason=f"{type(error).__name__}: {error}")]

    def _link(self, url: str) -> list[Result]:
        info = self.fetcher.probe(url)
        if isinstance(info, Playlist):
            return self._playlist(info)
        target = self.options.out / output_name(info.title, info.id)
        if self._done(target):
            return [Result(url, "skipped", str(target))]
        return [self._media(url, info, target)]

    def _playlist(self, playlist: Playlist) -> list[Result]:
        count = len(playlist.entries)
        if not count:
            raise SourceError("playlist is empty")
        self.log(f"  playlist: {playlist.title} ({count} videos)")
        directory = self.options.out / playlist_dir_name(playlist.title, playlist.id)
        results: list[Result] = []
        for position, entry in enumerate(playlist.entries, start=1):
            self.log(f"→ {entry.url}")
            results += self._guarded(entry.url, lambda: [self._entry(entry, directory, position, count)])
        return results

    def _entry(self, entry: Entry, directory: Path, position: int, count: int) -> Result:
        """One video of a playlist; a finished one is recognised by its id at any position."""
        existing = _transcript_of(directory, entry.id)
        if existing and self._done(existing):
            return Result(entry.url, "skipped", str(existing))
        info = self.fetcher.probe(entry.url)
        if isinstance(info, Playlist):
            raise SourceError("nested playlists and channels are not supported, pass a link to a playlist")
        target = directory / numbered_name(position, count, output_name(info.title, info.id))
        existing = target if target.exists() else _transcript_of(directory, info.id)
        if existing and self._done(existing):
            return Result(entry.url, "skipped", str(existing))
        result = self._media(entry.url, info, target)
        if existing and existing != target:
            existing.unlink()
        return result

    def _media(self, url: str, info: MediaInfo, target: Path) -> Result:
        segments: list[Segment] = []
        language = self.options.language or info.language
        method = ""
        if not self.options.whisper:
            track = subtitles.choose_track(
                list(info.subtitles), list(info.automatic), self.options.language, info.language
            )
            if track:
                kind = "automatic" if track.automatic else "authored"
                self.log(f"  platform subtitles ({kind}, {track.key})")
                text = self.fetcher.subtitles(info, track)
                segments = subtitles.parse_vtt(text) if text else []
                language = language or track.key
                method = f"platform subtitles ({kind})"
        if not segments:
            self.check_ffmpeg()
            with tempfile.TemporaryDirectory(prefix="huginn-") as directory:
                self.log("  downloading audio track")
                audio = self.fetcher.audio(url, Path(directory))
                segments, recognised = self._recognise(audio)
            language = self.options.language or recognised or info.language
            method = self.transcriber.label

        meta = Meta(info.title, url, language, method, info.duration, info.id)
        return self._write(url, target, meta, segments)

    def _file(self, path: Path) -> Result:
        target = self.options.out / f"{path.stem}.md"
        if self._done(target):
            return Result(str(path), "skipped", str(target))
        self.check_ffmpeg()
        segments, recognised = self._recognise(path)
        meta = Meta(path.stem, str(path.resolve()), self.options.language or recognised, self.transcriber.label)
        return self._write(str(path), target, meta, segments)

    def _done(self, target: Path) -> bool:
        if target.exists() and not self.options.force:
            self.log(f"  already done: {target}")
            return True
        return False

    def _recognise(self, audio: Path) -> tuple[list[Segment], str | None]:
        self.log(f"  speech recognition: {self.transcriber.label}")
        transcript = self.transcriber.transcribe(audio, self.options.language)
        segments = [s for s in transcript.segments if s.text.strip()]
        if not segments:
            raise SourceError("no speech found")
        return segments, transcript.language

    def _write(self, source: str, target: Path, meta: Meta, segments: list[Segment]) -> Result:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(meta, segments), encoding="utf-8")
        self.log(f"  done: {target}")
        return Result(source, "created", str(target))
