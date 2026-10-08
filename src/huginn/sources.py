from pathlib import Path

from huginn.models import Item, Result

MEDIA_EXTENSIONS = frozenset(
    ".mp3 .m4a .wav .flac .ogg .opus .aac .wma .aiff "
    ".mp4 .mkv .mov .webm .avi .m4v .wmv .flv .mpg .mpeg .ts .3gp".split()
)


def is_url(arg: str) -> bool:
    return arg.startswith(("http://", "https://"))


def resolve(args: list[str]) -> tuple[list[Item], list[Result]]:
    """Expand arguments into items; unrecognised ones are returned as failures."""
    items: list[Item] = []
    failures: list[Result] = []
    for arg in args:
        if is_url(arg):
            items.append(Item("url", arg))
            continue
        path = Path(arg).expanduser()
        if path.is_file():
            items.append(Item("file", str(path)))
        elif path.is_dir():
            media = sorted(
                p for p in path.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
            )
            if media:
                items.extend(Item("file", str(p)) for p in media)
            else:
                failures.append(Result(arg, "failed", reason="no media files in the directory"))
        else:
            failures.append(Result(arg, "failed", reason="path does not exist"))
    return items, failures
