import argparse
import sys
from pathlib import Path
from typing import Callable

from huginn.fetch import Fetcher
from huginn.models import Item, Result
from huginn.pipeline import Options, Pipeline
from huginn.sources import resolve
from huginn.transcriber import DEFAULT_MODEL, MODELS, MlxWhisper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="huginn",
        description="Транскрипты видео и аудио для быстрого скрининга.",
    )
    parser.add_argument("sources", nargs="+", metavar="ИСТОЧНИК", help="ссылка, медиафайл или директория")
    parser.add_argument("--out", type=Path, default=Path("transcripts"), metavar="DIR",
                        help="куда сохранять транскрипты (по умолчанию ./transcripts)")
    parser.add_argument("--whisper", action="store_true",
                        help="распознавать речь, даже если у ссылки есть субтитры")
    parser.add_argument("--model", default=DEFAULT_MODEL, metavar="NAME",
                        help=f"модель Whisper: {', '.join(MODELS)} или репозиторий Hugging Face "
                             f"(по умолчанию {DEFAULT_MODEL})")
    parser.add_argument("--lang", metavar="CODE", help="язык медиа, например ru или en (по умолчанию определяется сам)")
    parser.add_argument("--force", action="store_true", help="пересоздать уже готовые транскрипты")
    return parser


def summary(results: list[Result]) -> str:
    groups = [("Создано", "created"), ("Пропущено (уже готово)", "skipped"), ("Не удалось", "failed")]
    lines: list[str] = []
    for title, status in groups:
        matching = [r for r in results if r.status == status]
        if not matching:
            continue
        lines.append(f"{title}: {len(matching)}")
        for result in matching:
            detail = f"{result.source} — {result.reason}" if status == "failed" else result.path
            lines.append(f"  {detail}")
    return "\n".join(lines)


def run(items: list[Item], failures: list[Result], process: Callable[[Item], Result]) -> list[Result]:
    return failures + [process(item) for item in items]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = Options(out=args.out, whisper=args.whisper, language=args.lang, force=args.force)
    pipeline = Pipeline(
        options,
        Fetcher(),
        MlxWhisper(args.model),
        log=lambda message: print(message, file=sys.stderr, flush=True),
    )
    items, failures = resolve(args.sources)
    results = run(items, failures, pipeline.process)
    print(summary(results))
    return 1 if any(r.status == "failed" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
