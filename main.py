import logging
import os
import socket
import subprocess
import sys
import threading

import config as cfg
from services.audio import AudioService
from services.transcription import TranscriptionService
from services.llm import LLMService
from services.hotkey import HotkeyService
from services.paste import PasteService
from services.audio_mute import SystemMute
from ui.tray import TrayApp

_LOG = logging.getLogger("blitztext")


class BlitztextApp:
    def __init__(self) -> None:
        self._config = cfg.load()
        self._audio = AudioService()
        self._transcription: TranscriptionService | None = None
        self._llm: LLMService | None = None
        self._hotkey = HotkeyService()
        self._paste = PasteService()
        self._sysmute = SystemMute()
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
        _LOG.info("loading whisper model: %s", self._config["whisper_model"])
        try:
            self._transcription = TranscriptionService(self._config["whisper_model"])
            api_key = cfg.get_api_key()
            if api_key:
                self._llm = LLMService(api_key)
            self._tray.set_state("ready", "Bereit")
            _LOG.info("model loaded, ready (llm=%s)", "yes" if self._llm else "no")
        except Exception as e:
            self._tray.set_state("error", f"Fehler: {str(e)[:40]}")
            _LOG.exception("model load FAILED: %s", e)

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
        _LOG.info(
            "hotkeys registered: mode=%s transcribe=%s improve=%s",
            mode, self._config["hotkey_transcribe"], self._config["hotkey_improve"],
        )
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
            if self._recording:
                _LOG.info("hotkey ignored: already recording")
                return
            if self._transcription is None:
                _LOG.warning("hotkey pressed but model not ready -> ignored")
                self._flash_overlay("notready")
                return
            self._recording = True
            self._improve_mode = improve
        _LOG.info("hotkey -> recording start (improve=%s)", improve)
        self._audio.start_recording()
        self._sysmute.mute()  # Hintergrund-Ton stummschalten waehrend Aufnahme
        self._tray.set_state("recording", "Aufnahme läuft...")
        self._show_overlay("recording")

    def _stop(self) -> None:
        with self._lock:
            if not self._recording:
                return
            self._recording = False
        _LOG.info("hotkey -> recording stop, processing")
        self._tray.set_state("processing", "Wird verarbeitet...")
        threading.Thread(target=self._process, daemon=True).start()

    def _toggle(self, improve: bool) -> None:
        if self._recording:
            self._stop()
        else:
            self._start(improve=improve)

    def _process(self) -> None:
        wav_path = self._audio.stop_recording()
        self._sysmute.unmute()  # Ton sofort wieder freigeben, wenn Aufnahme endet
        if not wav_path:
            _LOG.warning("no audio captured (empty recording)")
            self._hide_overlay()
            self._tray.set_state("ready", "Bereit")
            return
        self._show_overlay("processing")
        empty = False
        try:
            text = self._transcription.transcribe(wav_path, self._config["language"])
            _LOG.info("transcribed %d chars", len(text))
            if text:
                if self._improve_mode and self._llm:
                    text = self._llm.improve_text(text)
                    _LOG.info("improved via llm -> %d chars", len(text))
                # Banner schliessen BEVOR eingefuegt wird, damit der Fokus
                # zurueck zum Zielfenster geht und Strg+V dort ankommt.
                self._hide_overlay()
                self._paste.paste(text)
                _LOG.info("pasted into active window")
            else:
                empty = True
                _LOG.info("transcript empty -> 'Nichts erkannt'")
            self._tray.set_state("ready", "Bereit")
        except Exception as e:
            self._tray.set_state("error", str(e)[:40])
            _LOG.exception("processing failed: %s", e)
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
        self._sysmute.unmute()  # Sicherheit: Ton nie stumm zuruecklassen
        self._hide_overlay()

    def run(self) -> None:
        threading.Thread(target=self._load_model, daemon=True).start()
        self._setup_hotkeys()
        self._tray.run()


_LOCK_PORT = 49219


def _acquire_single_instance():
    # Verhindert mehrere gleichzeitige Blitztext-Instanzen (Autostart +
    # manueller Start). Mehrere Instanzen wuerden sich um die globalen
    # Hotkeys und das Mikrofon streiten -> nichts funktioniert. Ein
    # belegter lokaler Port = es laeuft bereits eine Instanz.
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", _LOCK_PORT))
        lock.listen(1)
        return lock
    except OSError:
        return None


def _setup_logging() -> None:
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blitztext.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    _setup_logging()
    _instance_lock = _acquire_single_instance()
    if _instance_lock is None:
        _LOG.info("another instance already running -> exit (pid=%d)", os.getpid())
        sys.exit(0)
    _LOG.info("=== Blitztext start (pid=%d) ===", os.getpid())
    BlitztextApp().run()
