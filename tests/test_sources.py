from huginn.models import Item
from huginn.sources import resolve


def test_url():
    items, failures = resolve(["https://example.com/v"])
    assert items == [Item("url", "https://example.com/v")]
    assert failures == []


def test_file(tmp_path):
    f = tmp_path / "talk.mp4"
    f.touch()
    items, _ = resolve([str(f)])
    assert items == [Item("file", str(f))]


def test_directory_takes_only_top_level_media(tmp_path):
    (tmp_path / "b.MP3").touch()
    (tmp_path / "a.mkv").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "c.mp4").touch()
    items, failures = resolve([str(tmp_path)])
    assert [i.value for i in items] == [str(tmp_path / "a.mkv"), str(tmp_path / "b.MP3")]
    assert failures == []


def test_bad_sources_fail_without_blocking_others(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "readme.txt").touch()
    missing = str(tmp_path / "nope.mp4")
    items, failures = resolve([missing, "https://example.com/v", str(empty)])
    assert items == [Item("url", "https://example.com/v")]
    assert [(f.source, f.status, f.reason) for f in failures] == [
        (missing, "failed", "путь не существует"),
        (str(empty), "failed", "в директории нет медиафайлов"),
    ]
