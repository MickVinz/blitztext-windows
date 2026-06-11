from faster_whisper import WhisperModel


class TranscriptionService:
    def __init__(self, model_size: str = "tiny") -> None:
        try:
            self._model = WhisperModel(model_size, device="cuda", compute_type="int8")
        except Exception:
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, wav_path: str, language: str = "auto") -> str:
        lang = None if language == "auto" else language
        segments, _ = self._model.transcribe(wav_path, language=lang)
        return " ".join(seg.text.strip() for seg in segments).strip()
