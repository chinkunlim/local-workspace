import os
from unittest.mock import MagicMock, patch

import pytest

from skills.audio_transcriber.scripts.phases.p01_transcribe import vad_preprocess


@patch("pydub.AudioSegment.from_file")
@patch("pydub.silence.detect_nonsilent")
def test_vad_preprocess_under_limit(mock_detect, mock_from_file, tmp_path):
    # Setup mocks
    mock_audio = MagicMock()
    mock_audio.set_channels.return_value.set_frame_rate.return_value = mock_audio
    # original duration = 100 seconds (100,000 ms)
    mock_audio.__len__.return_value = 100000
    mock_from_file.return_value = mock_audio

    # Cleaned duration = 95 seconds (95,000 ms), meaning 5% silence removed (under 10% limit)
    mock_cleaned_audio = MagicMock()
    mock_cleaned_audio.__len__.return_value = 95000
    mock_audio.__getitem__.return_value = mock_cleaned_audio

    # Summing chunk list sums the items
    mock_cleaned_audio.export = MagicMock()

    # We mock detect_nonsilent to return one non-silent range
    mock_detect.return_value = [(0, 95000)]

    # Mock python builtin sum to return mock_cleaned_audio
    with patch(
        "skills.audio_transcriber.scripts.phases.p01_transcribe.sum",
        return_value=mock_cleaned_audio,
    ):
        cleaned_path, silence_ratio = vad_preprocess(
            audio_path="dummy.m4a",
            tmp_dir=str(tmp_path),
            max_removal_ratio=0.10,
        )

    # 5% silence removed is under the 10% limit, so VAD is applied
    assert cleaned_path.endswith("_vad.wav")
    assert pytest.approx(silence_ratio, 0.001) == 0.05
    assert mock_cleaned_audio.export.called


@patch("pydub.AudioSegment.from_file")
@patch("pydub.silence.detect_nonsilent")
def test_vad_preprocess_over_limit_fallback(mock_detect, mock_from_file, tmp_path):
    # Setup mocks
    mock_audio = MagicMock()
    mock_audio.set_channels.return_value.set_frame_rate.return_value = mock_audio
    # original duration = 100 seconds (100,000 ms)
    mock_audio.__len__.return_value = 100000
    mock_from_file.return_value = mock_audio

    # Cleaned duration = 85 seconds (85,000 ms), meaning 15% silence removed (over 10% limit)
    mock_cleaned_audio = MagicMock()
    mock_cleaned_audio.__len__.return_value = 85000
    mock_audio.__getitem__.return_value = mock_cleaned_audio

    mock_cleaned_audio.export = MagicMock()

    # We mock detect_nonsilent to return one non-silent range
    mock_detect.return_value = [(0, 85000)]

    # Mock python builtin sum to return mock_cleaned_audio
    with patch(
        "skills.audio_transcriber.scripts.phases.p01_transcribe.sum",
        return_value=mock_cleaned_audio,
    ):
        cleaned_path, silence_ratio = vad_preprocess(
            audio_path="dummy.m4a",
            tmp_dir=str(tmp_path),
            max_removal_ratio=0.10,
        )

    # 15% silence removed is over the 10% limit, so VAD falls back to original audio path
    assert cleaned_path == "dummy.m4a"
    assert silence_ratio == 0.0
    assert not mock_cleaned_audio.export.called
