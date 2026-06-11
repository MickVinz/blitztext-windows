import os
import subprocess
import sys
import threading

import config as cfg
from services.audio import AudioService
from services.transcription import TranscriptionService
from services.llm import LLMService
from services.hotkey import HotkeyService
from services.paste import PasteService
from ui.tray import TrayApp


class BlitztextApp:
    def __init__(self) -> None:
        self._config = cfg.load()
        self._audio = AudioService()
        self._transcription: TranscriptionService | None = None
        self._llm: LLMService | None = None
        self._hotkey = HotkeyService()
        self._paste = PasteService()
        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        self._tray = TrayApp(on_settings=self._open_settings, on_quit=self._quit)
        self._recording = False
        self._improve_mode = False
        self._lock = threading.Lock()
        self._settings_open = False
        self._overlay_proc: subprocess.Popen | None = None
        self._overlay_lock = threading.Lock()

    def _load_model(self) -> None:
        self._tray.set_state("processing", "Modell wird geladen...")
        try:
            self._transcription = TranscriptionService(self._config["whisper_model"])
            api_key = cfg.get_api_key()
            if api_key:
                self._llm = LLMService(api_key)
            self._tray.set_state("ready", "Bereit")
        except Exception as e:
            self._tray.set_state("error", f"Fehler: {str(e)[:40]}")

    def _show_overlay(self, mode: str) -> None:
        # Startet das Aufnahme-/Verarbeitungs-Banner als eigenen Prozess
        # (tkinter braucht eigenen Hauptthread). Ein bereits laufendes
        # Overlay wird zuvor beendet.
        with self._overlay_lock:
            self._hide_overlay_locked()
            try:
                self._overlay_proc = subprocess.Popen(
                    [sys.executable, "-m", "ui.overlay", mode],
                    cwd=self._root_dir,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                self._overlay_proc = None

    def _hide_overlay(self) -> None:
        with self._overlay_lock:
            self._hide_overlay_locked()

    def _flash_overlay(self, mode: str) -> None:
        # Kurze, selbst-schliessende Meldung (z.B. "Nichts erkannt"). Wird
        # NICHT getrackt/terminiert — der Overlay-Prozess beendet sich selbst.
        try:
            subprocess.Popen(
                [sys.executable, "-m", "ui.overlay", mode],
                cwd=self._root_dir,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            pass

    def _hide_overlay_locked(self) -> None:
        if self._overlay_proc and self._overlay_proc.poll() is None:
            try:
                self._overlay_proc.terminate()
            except Exception:
                pass
        self._overlay_proc = None

    def _setup_hotkeys(self) -> None:
        self._hotkey.unregister_all()
        mode = self._config["recording_mode"]
        if mode == "push_to_talk":
            self._hotkey.setup_ptt(
                self._config["hotkey_transcribe"],
                lambda: self._start(improve=False), self._stop)
            self._hotkey.setup_ptt(
                self._config["hotkey_improve"],
                lambda: self._start(improve=True), self._stop)
        else:
            self._hotkey.setup_toggle(
                self._config["hotkey_transcribe"],
                lambda: self._toggle(improve=False))
            self._hotkey.setup_toggle(
                self._config["hotkey_improve"],
                lambda: self._toggle(improve=True))

    def _start(self, improve: bool) -> None:
        with self._lock:
            if self._recording or self._transcription is None:
                return
            self._recording = True
            self._improve_mode = improve
        self._audio.start_recording()
        self._tray.set_state("recording", "Aufnahme läuft...")
        self._show_overlay("recording")

    def _stop(self) -> None:
        with self._lock:
            if not self._recording:
                return
            self._recording = False
        self._tray.set_state("processing", "Wird verarbeitet...")
        threading.Thread(target=self._process, daemon=True).start()

    def _toggle(self, improve: bool) -> None:
        if self._recording:
            self._stop()
        else:
            self._start(improve=improve)

    def _process(self) -> None:
        wav_path = self._audio.stop_recording()
        if not wav_path:
            self._hide_overlay()
            self._tray.set_state("ready", "Bereit")
            return
        self._show_overlay("processing")
        empty = False
        try:
            text = self._transcription.transcribe(wav_path, self._config["language"])
            if text:
                if self._improve_mode and self._llm:
                    text = self._llm.improve_text(text)
                self._paste.paste(text)
            else:
                empty = True
            self._tray.set_state("ready", "Bereit")
        except Exception as e:
            self._tray.set_state("error", str(e)[:40])
        finally:
            self._hide_overlay()
            if empty:
                # Rueckmeldung, dass nichts verstanden wurde (sonst passiert
                # sichtbar gar nichts und es wirkt wie ein Defekt).
                self._flash_overlay("empty")
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    def _open_settings(self) -> None:
        if self._settings_open:
            return
        self._settings_open = True
        old_model = self._config.get("whisper_model", "tiny")

        def run_settings():
            try:
                subprocess.run(
                    [sys.executable, "-m", "ui.settings"],
                    cwd=self._root_dir,
                )
                # Fenster geschlossen → Config neu laden und anwenden.
                self._config = cfg.load()
                api_key = cfg.get_api_key()
                self._llm = LLMService(api_key) if api_key else None
                self._setup_hotkeys()
                if self._config.get("whisper_model") != old_model:
                    self._load_model()
            finally:
                self._settings_open = False

        threading.Thread(target=run_settings, daemon=True).start()

    def _quit(self) -> None:
        self._hotkey.unregister_all()
        self._hide_overlay()

    def run(self) -> None:
        threading.Thread(target=self._load_model, daemon=True).start()
        self._setup_hotkeys()
        self._tray.run()


if __name__ == "__main__":
    BlitztextApp().run()
