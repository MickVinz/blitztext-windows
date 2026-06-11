from unittest.mock import MagicMock, patch


def _seg(text):
    s = MagicMock()
    s.text = text
    return s


def test_transcribe_joins_segments(tmp_path):
    wav = str(tmp_path / "t.wav")
    open(wav, "wb").close()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([_seg(" Hello"), _seg(" world")]), MagicMock())
    with patch("services.transcription.WhisperModel", return_value=mock_model):
        import importlib
        import services.transcription as m; importlib.reload(m)
        svc = m.TranscriptionService.__new__(m.TranscriptionService)
        svc._model = mock_model
        assert svc.transcribe(wav, language="en") == "Hello world"


def test_transcribe_auto_passes_none(tmp_path):
    wav = str(tmp_path / "t.wav")
    open(wav, "wb").close()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([_seg("Text")]), MagicMock())
    with patch("services.transcription.WhisperModel", return_value=mock_model):
        import importlib
        import services.transcription as m; importlib.reload(m)
        svc = m.TranscriptionService.__new__(m.TranscriptionService)
        svc._model = mock_model
        svc.transcribe(wav, language="auto")
    mock_model.transcribe.assert_called_once_with(wav, language=None)


def test_transcribe_empty_returns_empty(tmp_path):
    wav = str(tmp_path / "t.wav")
    open(wav, "wb").close()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([]), MagicMock())
    with patch("services.transcription.WhisperModel", return_value=mock_model):
        import importlib
        import services.transcription as m; importlib.reload(m)
        svc = m.TranscriptionService.__new__(m.TranscriptionService)
        svc._model = mock_model
        assert svc.transcribe(wav) == ""
