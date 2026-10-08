import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from huginn.models import Segment, SourceError

MODELS = {
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "small": "mlx-community/whisper-small-mlx",
}
DEFAULT_MODEL = "turbo"


@dataclass(frozen=True)
class Transcript:
    language: str | None
    segments: list[Segment]


class Transcriber(Protocol):
    label: str

    def transcribe(self, audio: Path, language: str | None) -> Transcript: ...


def resolve_model(name: str) -> str:
    """Map a short model name to its Hugging Face repository; other values pass through."""
    return MODELS.get(name, name)


class MlxWhisper:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.repo = resolve_model(model)
        self.label = "Whisper " + self.repo.removeprefix("mlx-community/whisper-").removesuffix("-mlx")

    def transcribe(self, audio: Path, language: str | None) -> Transcript:
        import mlx_whisper

        result = mlx_whisper.transcribe(
            str(audio), path_or_hf_repo=self.repo, language=language, verbose=False
        )
        segments = [Segment(s["start"], s["end"], s["text"]) for s in result["segments"]]
        return Transcript(result.get("language"), segments)


def require_ffmpeg(which: Callable[[str], str | None] = shutil.which) -> None:
    if which("ffmpeg") is None:
        raise SourceError(
            "ffmpeg not found — it is needed for speech recognition; install it: brew install ffmpeg"
        )
