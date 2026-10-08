from huginn.models import Segment
from huginn.render import Meta, moment_url, output_name, paragraphs, render, timecode


def seg(start, end, text):
    return Segment(start, end, text)


def test_paragraph_breaks_on_pause():
    result = paragraphs([seg(0, 3, "One."), seg(3.5, 6, " Two. "), seg(8, 10, "Three.")])
    assert [(p.start, p.text) for p in result] == [(0, "One. Two."), (8, "Three.")]


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
        title="Talk",
        source="https://www.youtube.com/watch?v=abc",
        language="ru",
        method="platform subtitles (automatic)",
        duration=600,
        media_id="abc",
    )
    text = render(meta, [seg(0, 4, "hello everyone"), seg(155, 158, "second part")])
    assert text == (
        "# Talk\n"
        "\n"
        "- Source: https://www.youtube.com/watch?v=abc\n"
        "- Duration: 10:00\n"
        "- Language: ru\n"
        "- Obtained via: platform subtitles (automatic)\n"
        "\n"
        "[[00:00]](https://youtu.be/abc?t=0) hello everyone\n"
        "\n"
        "[[02:35]](https://youtu.be/abc?t=155) second part\n"
    )


def test_render_recognised_local_file_longer_than_hour():
    meta = Meta(title="talk", source="/media/talk.mp4", language=None, method="Whisper large-v3-turbo")
    text = render(meta, [seg(0, 4, "Beginning."), seg(3734, 3740, "The end.")])
    assert text == (
        "# talk\n"
        "\n"
        "- Source: /media/talk.mp4\n"
        "- Duration: 1:02:20\n"
        "- Language: unknown\n"
        "- Obtained via: Whisper large-v3-turbo\n"
        "\n"
        "[0:00:00] Beginning.\n"
        "\n"
        "[1:02:14] The end.\n"
    )


def test_output_names():
    assert output_name("Vorlesung №1: «Einführung» / Teil 2?", "dQw4-w9_WgX") == "Vorlesung-1-Einführung-Teil-2-dQw4-w9_WgX.md"
    assert output_name("talk") == "talk.md"
    assert output_name("???", "x1") == "media-x1.md"
    assert output_name("Same title", "a1") != output_name("Same title", "b2")
    assert len(output_name("é" * 300, "id")) == 80 + len("-id.md")
