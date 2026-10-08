from huginn.models import Segment
from huginn.render import Meta, moment_url, output_name, paragraphs, render, timecode


def seg(start, end, text):
    return Segment(start, end, text)


def test_paragraph_breaks_on_pause():
    result = paragraphs([seg(0, 3, "Раз."), seg(3.5, 6, " Два. "), seg(8, 10, "Три.")])
    assert [(p.start, p.text) for p in result] == [(0, "Раз. Два."), (8, "Три.")]


def test_continuous_speech_is_split_by_duration():
    segments = [seg(i * 10, i * 10 + 10, f"s{i}") for i in range(13)]
    result = paragraphs(segments)
    assert [p.start for p in result] == [0, 60, 120]
    assert result[0].text == "s0 s1 s2 s3 s4 s5"


def test_no_segments_no_paragraphs():
    assert paragraphs([]) == []
    assert paragraphs([seg(0, 1, "   ")]) == []


def test_timecode_formats():
    assert timecode(155) == "02:35"
    assert timecode(3734) == "1:02:14"
    assert timecode(155, with_hours=True) == "0:02:35"


def test_moment_url_only_for_youtube():
    assert moment_url("https://www.youtube.com/watch?v=abc", "abc", 155.7) == "https://youtu.be/abc?t=155"
    assert moment_url("https://youtu.be/abc", "abc", 5) == "https://youtu.be/abc?t=5"
    assert moment_url("https://vimeo.com/123", "123", 5) is None
    assert moment_url("/home/me/talk.mp4", None, 5) is None


def test_render_subtitles_from_youtube():
    meta = Meta(
        title="Доклад",
        source="https://www.youtube.com/watch?v=abc",
        language="ru",
        method="субтитры платформы (автоматические)",
        duration=600,
        media_id="abc",
    )
    text = render(meta, [seg(0, 4, "привет всем"), seg(155, 158, "вторая часть")])
    assert text == (
        "# Доклад\n"
        "\n"
        "- Источник: https://www.youtube.com/watch?v=abc\n"
        "- Длительность: 10:00\n"
        "- Язык: ru\n"
        "- Получено: субтитры платформы (автоматические)\n"
        "\n"
        "[[00:00]](https://youtu.be/abc?t=0) привет всем\n"
        "\n"
        "[[02:35]](https://youtu.be/abc?t=155) вторая часть\n"
    )


def test_render_recognised_local_file_longer_than_hour():
    meta = Meta(title="talk", source="/media/talk.mp4", language=None, method="Whisper large-v3-turbo")
    text = render(meta, [seg(0, 4, "Начало."), seg(3734, 3740, "Конец.")])
    assert text == (
        "# talk\n"
        "\n"
        "- Источник: /media/talk.mp4\n"
        "- Длительность: 1:02:20\n"
        "- Язык: не определён\n"
        "- Получено: Whisper large-v3-turbo\n"
        "\n"
        "[0:00:00] Начало.\n"
        "\n"
        "[1:02:14] Конец.\n"
    )


def test_output_names():
    assert output_name("Лекция №1: «Введение» / часть 2?", "dQw4-w9_WgX") == "Лекция-1-Введение-часть-2-dQw4-w9_WgX.md"
    assert output_name("talk") == "talk.md"
    assert output_name("???", "x1") == "media-x1.md"
    assert output_name("Тот же заголовок", "a1") != output_name("Тот же заголовок", "b2")
    assert len(output_name("я" * 300, "id")) == 80 + len("-id.md")
