from pathlib import Path

from huginn import cli
from huginn.fetch import Entry, MediaInfo, Playlist
from huginn.models import Item, Result, SourceError


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
        "Created: 1\n  out/a.md\n"
        "Skipped (already done): 1\n  out/b.md\n"
        "Failed: 1\n  c — Video unavailable"
    )


class StubPipeline:
    def __init__(self, options, fetcher, transcriber, log):
        self.log = log

    def process(self, item: Item) -> list[Result]:
        self.log(f"→ {item.value}")
        if "bad" in item.value:
            return [Result(item.value, "failed", reason="Video unavailable")]
        return [Result(item.value, "created", f"out/{item.value[-1]}.md")]


def test_one_failure_does_not_stop_the_batch(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Pipeline", StubPipeline)
    code = cli.main(["https://x/1", "https://x/bad", "https://x/3", "/no/such/file.mp4"])
    out, err = capsys.readouterr()
    assert code == 1
    assert "Created: 2\n  out/1.md\n  out/3.md" in out
    assert "/no/such/file.mp4 — path does not exist" in out
    assert "https://x/bad — Video unavailable" in out
    assert err.splitlines() == ["→ https://x/1", "→ https://x/bad", "→ https://x/3"]


def test_exit_code_zero_when_everything_done(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Pipeline", StubPipeline)
    assert cli.main(["https://x/1"]) == 0
    assert capsys.readouterr().out == "Created: 1\n  out/1.md\n"


class PlaylistFetcher:
    def probe(self, url):
        if "list=" in url:
            return Playlist("PL1", "Course", [Entry(f"https://x/watch?v={i}", i) for i in ("v1", "bad", "v3")])
        if "bad" in url:
            raise SourceError("Video unavailable")
        media_id = url.rsplit("=", 1)[1]
        return MediaInfo(id=media_id, title="Talk", url=url, duration=60, language="en", automatic={"en": []})

    def subtitles(self, info, track):
        return "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nsubtitle text\n"


def test_playlist_yields_a_summary_line_per_video(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "Fetcher", PlaylistFetcher)
    monkeypatch.setattr(cli, "MlxWhisper", lambda model: None)
    code = cli.main(["https://x/playlist?list=PL1", "--out", str(tmp_path)])
    out, err = capsys.readouterr()
    directory = tmp_path / "Course-PL1"
    assert code == 1
    assert out == (
        f"Created: 2\n  {directory / '01-Talk-v1.md'}\n  {directory / '03-Talk-v3.md'}\n"
        "Failed: 1\n  https://x/watch?v=bad — Video unavailable\n"
    )
    assert "  playlist: Course (3 videos)" in err.splitlines()
