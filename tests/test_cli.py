from pathlib import Path

from huginn import cli
from huginn.models import Item, Result


def test_arguments():
    args = cli.build_parser().parse_args(
        ["a.mp4", "https://x/y", "--out", "notes", "--whisper", "--model", "small", "--lang", "ru", "--force"])
    assert args.sources == ["a.mp4", "https://x/y"]
    assert (args.out, args.whisper, args.model, args.lang, args.force) == (Path("notes"), True, "small", "ru", True)
    defaults = cli.build_parser().parse_args(["a.mp4"])
    assert (defaults.out, defaults.whisper, defaults.model, defaults.lang, defaults.force) == (
        Path("transcripts"), False, "turbo", None, False)


def test_summary_lists_created_skipped_and_failed():
    text = cli.summary([
        Result("a", "created", "out/a.md"),
        Result("b", "skipped", "out/b.md"),
        Result("c", "failed", reason="Video unavailable"),
    ])
    assert text == (
        "Создано: 1\n  out/a.md\n"
        "Пропущено (уже готово): 1\n  out/b.md\n"
        "Не удалось: 1\n  c — Video unavailable"
    )


class StubPipeline:
    def __init__(self, options, fetcher, transcriber, log):
        self.log = log

    def process(self, item: Item) -> Result:
        self.log(f"→ {item.value}")
        if "bad" in item.value:
            return Result(item.value, "failed", reason="Video unavailable")
        return Result(item.value, "created", f"out/{item.value[-1]}.md")


def test_one_failure_does_not_stop_the_batch(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Pipeline", StubPipeline)
    code = cli.main(["https://x/1", "https://x/bad", "https://x/3", "/no/such/file.mp4"])
    out, err = capsys.readouterr()
    assert code == 1
    assert "Создано: 2\n  out/1.md\n  out/3.md" in out
    assert "/no/such/file.mp4 — путь не существует" in out
    assert "https://x/bad — Video unavailable" in out
    assert err.splitlines() == ["→ https://x/1", "→ https://x/bad", "→ https://x/3"]


def test_exit_code_zero_when_everything_done(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Pipeline", StubPipeline)
    assert cli.main(["https://x/1"]) == 0
    assert capsys.readouterr().out == "Создано: 1\n  out/1.md\n"
