import pytest

from huginn.models import SourceError
from huginn.transcriber import MlxWhisper, require_ffmpeg, resolve_model


def test_short_model_names_map_to_repositories():
    assert resolve_model("turbo") == "mlx-community/whisper-large-v3-turbo"
    assert resolve_model("large-v3") == "mlx-community/whisper-large-v3-mlx"
    assert resolve_model("small") == "mlx-community/whisper-small-mlx"
    assert resolve_model("someone/custom-whisper") == "someone/custom-whisper"


def test_label_names_the_model():
    assert MlxWhisper().label == "Whisper large-v3-turbo"
    assert MlxWhisper("large-v3").label == "Whisper large-v3"
    assert MlxWhisper("someone/custom").label == "Whisper someone/custom"


def test_missing_ffmpeg_explains_how_to_install():
    with pytest.raises(SourceError, match="ffmpeg not found.*brew install ffmpeg"):
        require_ffmpeg(which=lambda name: None)


def test_present_ffmpeg_passes():
    require_ffmpeg(which=lambda name: "/opt/homebrew/bin/ffmpeg")
