import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from huginn import subtitles
from huginn.fetch import Fetcher
from huginn.models import Item, Result, Segment, SourceError
from huginn.render import Meta, output_name, render
from huginn.transcriber import Transcriber, require_ffmpeg


@dataclass(frozen=True)
class Options:
    out: Path = Path("transcripts")
    whisper: bool = False
    language: str | None = None
    force: bool = False


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

    def process(self, item: Item) -> Result:
        """Обрабатывает один источник; любая ошибка становится результатом, а не исключением."""
        self.log(f"→ {item.value}")
        try:
            if item.kind == "url":
                return self._url(item.value)
            return self._file(Path(item.value))
        except SourceError as error:
            return Result(item.value, "failed", reason=str(error))
        except Exception as error:
            return Result(item.value, "failed", reason=f"{type(error).__name__}: {error}")

    def _url(self, url: str) -> Result:
        info = self.fetcher.probe(url)
        target = self.options.out / output_name(info.title, info.id)
        if self._done(target):
            return Result(url, "skipped", str(target))

        segments: list[Segment] = []
        language = self.options.language or info.language
        method = ""
        if not self.options.whisper:
            track = subtitles.choose_track(
                list(info.subtitles), list(info.automatic), self.options.language, info.language
            )
            if track:
                kind = "автоматические" if track.automatic else "авторские"
                self.log(f"  субтитры платформы ({kind}, {track.key})")
                text = self.fetcher.subtitles(info, track)
                segments = subtitles.parse_vtt(text) if text else []
                language = language or track.key
                method = f"субтитры платформы ({kind})"
        if not segments:
            self.check_ffmpeg()
            with tempfile.TemporaryDirectory(prefix="huginn-") as directory:
                self.log("  загрузка аудиодорожки")
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
            self.log(f"  уже готово: {target}")
            return True
        return False

    def _recognise(self, audio: Path) -> tuple[list[Segment], str | None]:
        self.log(f"  распознавание речи: {self.transcriber.label}")
        transcript = self.transcriber.transcribe(audio, self.options.language)
        segments = [s for s in transcript.segments if s.text.strip()]
        if not segments:
            raise SourceError("речь не найдена")
        return segments, transcript.language

    def _write(self, source: str, target: Path, meta: Meta, segments: list[Segment]) -> Result:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(meta, segments), encoding="utf-8")
        self.log(f"  готово: {target}")
        return Result(source, "created", str(target))
