import html
import re
from dataclasses import dataclass

from huginn.models import Segment

_TIMING = re.compile(r"^\s*((?:\d+:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d+:)?\d{2}:\d{2}[.,]\d{3})")
_TAG = re.compile(r"<[^>]*>")


@dataclass(frozen=True)
class Track:
    key: str
    automatic: bool


def _seconds(stamp: str) -> float:
    parts = stamp.replace(",", ".").split(":")
    seconds = float(parts[-1]) + int(parts[-2]) * 60
    if len(parts) == 3:
        seconds += int(parts[0]) * 3600
    return seconds


def parse_vtt(text: str) -> list[Segment]:
    """Разбирает VTT в сегменты, снимая разметку и повторы строк между соседними репликами.

    Автоматические субтитры YouTube «прокручиваются»: каждая реплика повторяет
    последнюю строку предыдущей. В сегмент попадают только новые строки реплики.
    """
    segments: list[Segment] = []
    previous: list[str] = []
    blocks = re.split(r"\n{2,}", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = block.split("\n")
        for index, line in enumerate(lines):
            timing = _TIMING.match(line)
            if timing:
                break
        else:
            continue
        cue = [" ".join(html.unescape(_TAG.sub("", raw)).split()) for raw in lines[index + 1 :]]
        cue = [line for line in cue if line]
        fresh = [line for line in cue if line not in previous]
        if cue:
            previous = cue
        if fresh:
            segments.append(Segment(_seconds(timing[1]), _seconds(timing[2]), " ".join(fresh)))
    return segments


def _match(keys: list[str], language: str, prefer_orig: bool) -> str | None:
    candidates = [f"{language}-orig"] if prefer_orig else []
    candidates.append(language)
    for candidate in candidates:
        if candidate in keys:
            return candidate
    return next((key for key in keys if key.startswith(f"{language}-")), None)


def choose_track(
    manual: list[str],
    automatic: list[str],
    requested: str | None,
    media_language: str | None,
) -> Track | None:
    """Выбирает дорожку субтитров на языке оригинала; авторская предпочитается автоматической."""
    manual = [key for key in manual if key != "live_chat"]
    language = requested or media_language
    if language:
        language = language.split("-")[0]
        key = _match(manual, language, prefer_orig=False)
        if key:
            return Track(key, automatic=False)
        key = _match(automatic, language, prefer_orig=True)
        if key:
            return Track(key, automatic=True)
        return None
    if len(manual) == 1:
        return Track(manual[0], automatic=False)
    return None
