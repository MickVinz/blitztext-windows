import os

from faster_whisper import WhisperModel


class TranscriptionService:
    def __init__(self, model_size: str = "tiny") -> None:
        self._model = self._load_model(model_size)

    @staticmethod
    def _load_model(model_size: str) -> WhisperModel:
        # CUDA nur nutzen, wenn die GPU/Lib es wirklich kann. Auf aelteren
        # Karten (z.B. GTX 750 Ti) oder ohne CUDA-Toolkit schlaegt schon die
        # Konstruktion fehl -> sauberer CPU-Fallback mit allen Kernen.
        for compute_type in ("float16", "int8"):
            try:
                return WhisperModel(model_size, device="cuda", compute_type=compute_type)
            except Exception:
                continue
        return WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=os.cpu_count() or 4,
        )

    def transcribe(self, wav_path: str, language: str = "auto") -> str:
        lang = None if language == "auto" else language
        # beam_size=1 ist auf der CPU spuerbar schneller als der Default (5)
        # und fuer kurze Diktate ausreichend genau.
        segments, _ = self._model.transcribe(wav_path, language=lang, beam_size=1)
        return " ".join(seg.text.strip() for seg in segments).strip()
