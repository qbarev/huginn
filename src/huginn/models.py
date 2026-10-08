from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Item:
    kind: Literal["url", "file"]
    value: str


@dataclass(frozen=True)
class Result:
    source: str
    status: Literal["created", "skipped", "failed"]
    path: str | None = None
    reason: str | None = None


class SourceError(Exception):
    """A source could not be processed; the message is the reason shown in the summary."""
