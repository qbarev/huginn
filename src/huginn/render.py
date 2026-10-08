import re
from dataclasses import dataclass
from urllib.parse import urlparse

from huginn.models import Segment

PAUSE_SECONDS = 2.0
MAX_PARAGRAPH_SECONDS = 60.0
MAX_NAME_LENGTH = 80


@dataclass(frozen=True)
class Paragraph:
    start: float
    text: str


@dataclass(frozen=True)
class Meta:
    title: str
    source: str
    language: str | None
    method: str
    duration: float | None = None
    media_id: str | None = None


def paragraphs(segments: list[Segment]) -> list[Paragraph]:
    result: list[Paragraph] = []
    current: list[Segment] = []

    def flush() -> None:
        text = " ".join(" ".join(s.text for s in current).split())
        if text:
            result.append(Paragraph(current[0].start, text))
        current.clear()

    for segment in segments:
        if current and (
            segment.start - current[-1].end >= PAUSE_SECONDS
            or segment.start - current[0].start >= MAX_PARAGRAPH_SECONDS
        ):
            flush()
        current.append(segment)
    if current:
        flush()
    return result


def timecode(seconds: float, with_hours: bool = False) -> str:
    total = int(seconds)
    hours, minutes, secs = total // 3600, total % 3600 // 60, total % 60
    if with_hours or hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def moment_url(source: str, media_id: str | None, seconds: float) -> str | None:
    """Ссылка на момент медиа; поддерживается только YouTube."""
    host = (urlparse(source).hostname or "").lower()
    is_youtube = host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    if not is_youtube or not media_id:
        return None
    return f"https://youtu.be/{media_id}?t={int(seconds)}"


def render(meta: Meta, segments: list[Segment]) -> str:
    duration = meta.duration
    if duration is None and segments:
        duration = segments[-1].end
    with_hours = duration is not None and duration >= 3600

    lines = [f"# {meta.title}", "", f"- Источник: {meta.source}"]
    if duration is not None:
        lines.append(f"- Длительность: {timecode(duration, with_hours)}")
    lines.append(f"- Язык: {meta.language or 'не определён'}")
    lines.append(f"- Получено: {meta.method}")

    for paragraph in paragraphs(segments):
        stamp = f"[{timecode(paragraph.start, with_hours)}]"
        link = moment_url(meta.source, meta.media_id, paragraph.start)
        if link:
            stamp = f"[{stamp}]({link})"
        lines += ["", f"{stamp} {paragraph.text}"]
    return "\n".join(lines) + "\n"


def _safe(text: str) -> str:
    return re.sub(r"[^\w]+", "-", text).strip("-")


def output_name(title: str, media_id: str | None = None) -> str:
    """Имя файла транскрипта: для ссылок к названию добавляется идентификатор медиа."""
    name = _safe(title)[:MAX_NAME_LENGTH].strip("-") or "media"
    if media_id:
        name = f"{name}-{_safe(media_id) or 'id'}"
    return f"{name}.md"
