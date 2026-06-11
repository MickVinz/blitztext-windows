# Blitztext Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows Python app that records speech via global hotkey, transcribes with faster-whisper locally, optionally improves text with Claude Haiku, and pastes into the active window.

**Architecture:** Single-process, service-module pattern. `BlitztextApp` in `main.py` wires together AudioService, TranscriptionService, LLMService, HotkeyService, PasteService, and TrayApp. Audio recording runs in a sounddevice background thread; transcription and LLM run in a daemon thread after recording stops.

**Tech Stack:** Python 3.11+, faster-whisper (STT/CUDA), anthropic SDK (claude-haiku-4-5), sounddevice, keyboard, pystray, pywin32, Pillow, keyring, tkinter.

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | App entry point, orchestrates all services |
| `config.py` | Load/save JSON config, keyring for API key |
| `services/audio.py` | Mic recording → WAV tempfile |
| `services/transcription.py` | faster-whisper wrapper → plain text |
| `services/llm.py` | Claude Haiku API → improved text |
| `services/hotkey.py` | Global PTT + toggle hotkey registration |
| `services/paste.py` | Clipboard + Ctrl+V paste into active window |
| `ui/tray.py` | pystray icon + menu, state-based icon colors |
| `ui/settings.py` | tkinter settings window |
| `assets/icons.py` | Pillow-generated colored circle icons |
| `requirements.txt` | Dependencies |
| `tests/test_config.py` | Config load/save/defaults/keyring |
| `tests/test_transcription.py` | TranscriptionService with mocked model |
| `tests/test_llm.py` | LLMService with mocked anthropic client |
| `tests/test_paste.py` | PasteService with mocked win32 |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `services/__init__.py`, `ui/__init__.py`, `tests/__init__.py`, `assets/__init__.py`

- [ ] **Step 1: Create directories and init files**

Run in `E:\Blitztext Push to talk`:
```powershell
New-Item -ItemType Directory -Force -Path services, ui, tests, assets
New-Item -ItemType File -Force -Path services/__init__.py, ui/__init__.py, tests/__init__.py, assets/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
faster-whisper>=1.0.3
anthropic>=0.43.0
sounddevice>=0.4.6
keyboard>=0.13.5
pystray>=0.19.5
pywin32>=306
Pillow>=10.4.0
keyring>=25.5.0
numpy>=1.26.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 3: Install dependencies**

```powershell
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 4: Verify imports**

```powershell
python -c "import faster_whisper; import anthropic; import sounddevice; import keyboard; import pystray; import win32clipboard; import keyring; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```
git init
git add requirements.txt services/__init__.py ui/__init__.py tests/__init__.py assets/__init__.py
git commit -m "feat: project scaffolding"
```

---

### Task 2: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:
```python
import json
import pytest
from unittest.mock import MagicMock


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_FILE", str(tmp_path / "config.json"))
    import importlib, config
    importlib.reload(config)
    result = config.load()
    assert result["recording_mode"] == "push_to_talk"
    assert result["hotkey_transcribe"] == "ctrl+shift+space"
    assert result["hotkey_improve"] == "ctrl+shift+alt+space"
    assert result["whisper_model"] == "tiny"
    assert result["language"] == "auto"


def test_load_merges_with_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"whisper_model": "base", "language": "de"}))
    monkeypatch.setattr("config.CONFIG_FILE", str(cfg_file))
    import importlib, config
    importlib.reload(config)
    result = config.load()
    assert result["whisper_model"] == "base"
    assert result["language"] == "de"
    assert result["recording_mode"] == "push_to_talk"


def test_save_writes_json(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("config.CONFIG_FILE", str(cfg_file))
    import importlib, config
    importlib.reload(config)
    config.save({"recording_mode": "toggle", "whisper_model": "tiny",
                 "hotkey_transcribe": "ctrl+shift+space",
                 "hotkey_improve": "ctrl+shift+alt+space", "language": "de"})
    data = json.loads(cfg_file.read_text())
    assert data["recording_mode"] == "toggle"


def test_get_api_key_returns_none_when_not_set(monkeypatch):
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = None
    monkeypatch.setattr("config.keyring", mock_kr)
    import importlib, config
    importlib.reload(config)
    assert config.get_api_key() is None


def test_set_and_get_api_key(monkeypatch):
    stored = {}
    mock_kr = MagicMock()
    mock_kr.get_password.side_effect = lambda s, u: stored.get((s, u))
    mock_kr.set_password.side_effect = lambda s, u, v: stored.update({(s, u): v})
    monkeypatch.setattr("config.keyring", mock_kr)
    import importlib, config
    importlib.reload(config)
    config.set_api_key("sk-test")
    assert config.get_api_key() == "sk-test"
```

- [ ] **Step 2: Run — verify fail**

```powershell
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Create config.py**

```python
import json
import os
import keyring

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_KEYRING_SERVICE = "blitztext"
_KEYRING_USER = "claude_api_key"

_DEFAULTS = {
    "recording_mode": "push_to_talk",
    "hotkey_transcribe": "ctrl+shift+space",
    "hotkey_improve": "ctrl+shift+alt+space",
    "whisper_model": "tiny",
    "language": "auto",
}


def load() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return _DEFAULTS.copy()
    with open(CONFIG_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {**_DEFAULTS, **data}


def save(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_api_key() -> str | None:
    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)


def set_api_key(key: str) -> None:
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, key)
```

- [ ] **Step 4: Run — verify pass**

```powershell
pytest tests/test_config.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```
git add config.py tests/test_config.py
git commit -m "feat: config module (JSON + keyring)"
```

---

### Task 3: Audio Service

**Files:**
- Create: `services/audio.py`

- [ ] **Step 1: Create services/audio.py**

```python
import tempfile
import wave
import numpy as np
import sounddevice as sd


class AudioService:
    SAMPLERATE = 16000
    CHANNELS = 1
    DTYPE = "int16"

    def __init__(self) -> None:
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def start_recording(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.SAMPLERATE,
            channels=self.CHANNELS,
            dtype=self.DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        self._frames.append(indata.copy())

    def stop_recording(self) -> str | None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return None
        audio = np.concatenate(self._frames, axis=0)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLERATE)
            wf.writeframes(audio.tobytes())
        return tmp.name
```

- [ ] **Step 2: Smoke test mic**

```powershell
python -c "import time; from services.audio import AudioService; a=AudioService(); a.start_recording(); time.sleep(3); print(a.stop_recording())"
```

Expected: prints a `.wav` temp path.

- [ ] **Step 3: Commit**

```
git add services/audio.py
git commit -m "feat: audio recording service (sounddevice)"
```

---

### Task 4: Transcription Service

**Files:**
- Create: `services/transcription.py`
- Create: `tests/test_transcription.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_transcription.py`:
```python
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
```

- [ ] **Step 2: Run — verify fail**

```powershell
pytest tests/test_transcription.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.transcription'`

- [ ] **Step 3: Create services/transcription.py**

```python
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
```

- [ ] **Step 4: Run — verify pass**

```powershell
pytest tests/test_transcription.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```
git add services/transcription.py tests/test_transcription.py
git commit -m "feat: transcription service (faster-whisper, CUDA)"
```

---

### Task 5: LLM Service

**Files:**
- Create: `services/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm.py`:
```python
from unittest.mock import MagicMock, patch


def _mock_client(text):
    c = MagicMock()
    c.messages.create.return_value.content = [MagicMock(text=text)]
    return c


def test_improve_strips_whitespace():
    with patch("services.llm.anthropic.Anthropic", return_value=_mock_client("  Result.  ")):
        import importlib, services.llm as m; importlib.reload(m)
        assert m.LLMService("sk-x").improve_text("raw") == "Result."


def test_uses_haiku_model():
    mock_c = _mock_client("OK")
    with patch("services.llm.anthropic.Anthropic", return_value=mock_c):
        import importlib, services.llm as m; importlib.reload(m)
        m.LLMService("sk-x").improve_text("test")
    kw = mock_c.messages.create.call_args.kwargs
    assert kw["model"] == "claude-haiku-4-5"
    assert kw["max_tokens"] == 1024


def test_raw_text_in_prompt():
    mock_c = _mock_client("OK")
    with patch("services.llm.anthropic.Anthropic", return_value=mock_c):
        import importlib, services.llm as m; importlib.reload(m)
        m.LLMService("sk-x").improve_text("mein rohtext")
    content = mock_c.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "mein rohtext" in content
```

- [ ] **Step 2: Run — verify fail**

```powershell
pytest tests/test_llm.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.llm'`

- [ ] **Step 3: Create services/llm.py**

```python
import anthropic


class LLMService:
    _SYSTEM = (
        "Du bist ein präziser Text-Editor. "
        "Schreibe diktierten Text zu sauberem, natürlichem Deutsch um. "
        "Korrigiere Grammatik, Zeichensetzung und Satzstruktur. "
        "Behalte Inhalt und Ton bei. "
        "Antworte ausschließlich mit dem verbesserten Text, ohne Erklärungen."
    )

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def improve_text(self, text: str) -> str:
        response = self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=self._SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        return response.content[0].text.strip()
```

- [ ] **Step 4: Run — verify pass**

```powershell
pytest tests/test_llm.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```
git add services/llm.py tests/test_llm.py
git commit -m "feat: LLM text improvement (Claude Haiku)"
```

---

### Task 6: Paste Service

**Files:**
- Create: `services/paste.py`
- Create: `tests/test_paste.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_paste.py`:
```python
import sys
from unittest.mock import MagicMock, patch


def _make_mocks():
    mock_cb = MagicMock()
    mock_con = MagicMock()
    mock_con.CF_UNICODETEXT = 13
    mock_con.VK_CONTROL = 0x11
    mock_con.KEYEVENTF_KEYUP = 0x0002
    mock_api = MagicMock()
    mock_time = MagicMock()
    return mock_cb, mock_con, mock_api, mock_time


def test_paste_sets_clipboard():
    mock_cb, mock_con, mock_api, mock_time = _make_mocks()
    with patch.dict(sys.modules, {"win32clipboard": mock_cb, "win32con": mock_con,
                                   "win32api": mock_api, "time": mock_time}):
        import importlib, services.paste as m; importlib.reload(m)
        m.PasteService().paste("Hallo Welt")
    mock_cb.OpenClipboard.assert_called_once()
    mock_cb.SetClipboardText.assert_called_once_with("Hallo Welt", 13)
    mock_cb.CloseClipboard.assert_called_once()


def test_paste_sends_four_key_events():
    mock_cb, mock_con, mock_api, mock_time = _make_mocks()
    with patch.dict(sys.modules, {"win32clipboard": mock_cb, "win32con": mock_con,
                                   "win32api": mock_api, "time": mock_time}):
        import importlib, services.paste as m; importlib.reload(m)
        m.PasteService().paste("Test")
    assert mock_api.keybd_event.call_count == 4
```

- [ ] **Step 2: Run — verify fail**

```powershell
pytest tests/test_paste.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.paste'`

- [ ] **Step 3: Create services/paste.py**

```python
import time
import win32clipboard
import win32con
import win32api


class PasteService:
    def paste(self, text: str) -> None:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord("V"), 0, 0, 0)
        win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
```

- [ ] **Step 4: Run — verify pass**

```powershell
pytest tests/test_paste.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```
git add services/paste.py tests/test_paste.py
git commit -m "feat: paste service (win32 clipboard + Ctrl+V)"
```

---

### Task 7: Hotkey Service

**Files:**
- Create: `services/hotkey.py`

- [ ] **Step 1: Create services/hotkey.py**

```python
import keyboard


class HotkeyService:
    def __init__(self) -> None:
        self._hooks: list = []

    def setup_ptt(self, hotkey: str, on_start, on_stop) -> None:
        keys = [k.strip().lower() for k in hotkey.split("+")]
        trigger = keys[-1]
        modifiers = keys[:-1]
        active = [False]

        def on_event(e):
            if e.name != trigger:
                return
            if e.event_type == keyboard.KEY_DOWN:
                if not active[0] and all(keyboard.is_pressed(m) for m in modifiers):
                    active[0] = True
                    on_start()
            elif e.event_type == keyboard.KEY_UP:
                if active[0]:
                    active[0] = False
                    on_stop()

        self._hooks.append(keyboard.hook(on_event))

    def setup_toggle(self, hotkey: str, on_toggle) -> None:
        self._hooks.append(keyboard.add_hotkey(hotkey, on_toggle))

    def unregister_all(self) -> None:
        for h in self._hooks:
            try:
                keyboard.unhook(h)
            except Exception:
                pass
        self._hooks.clear()
```

- [ ] **Step 2: Smoke test PTT**

```powershell
python -c "
import keyboard
from services.hotkey import HotkeyService
h = HotkeyService()
h.setup_ptt('ctrl+shift+space', lambda: print('START'), lambda: print('STOP'))
print('Hold Ctrl+Shift+Space. Ctrl+C to quit.')
keyboard.wait()
"
```

Expected: `START` on press, `STOP` on release.

Note: If no output, try running PowerShell as Administrator.

- [ ] **Step 3: Commit**

```
git add services/hotkey.py
git commit -m "feat: hotkey service (PTT + toggle)"
```

---

### Task 8: Tray Icons

**Files:**
- Create: `assets/icons.py`

- [ ] **Step 1: Create assets/icons.py**

```python
from PIL import Image, ImageDraw

_SIZE = 64
_MARGIN = 6


def _circle(color: str) -> Image.Image:
    img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([_MARGIN, _MARGIN, _SIZE - _MARGIN, _SIZE - _MARGIN], fill=color)
    return img


ICONS: dict[str, Image.Image] = {
    "ready":      _circle("#4CAF50"),
    "recording":  _circle("#F44336"),
    "processing": _circle("#FFC107"),
    "error":      _circle("#9E9E9E"),
}
```

- [ ] **Step 2: Verify icons**

```powershell
python -c "from assets.icons import ICONS; print(list(ICONS.keys()))"
```

Expected: `['ready', 'recording', 'processing', 'error']`

- [ ] **Step 3: Commit**

```
git add assets/icons.py assets/__init__.py
git commit -m "feat: tray icon assets (Pillow)"
```

---

### Task 9: Tray App

**Files:**
- Create: `ui/tray.py`

- [ ] **Step 1: Create ui/tray.py**

```python
import pystray
from assets.icons import ICONS


class TrayApp:
    def __init__(self, on_settings, on_quit) -> None:
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._status = "Wird geladen..."
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(f"● {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Einstellungen...", lambda icon, item: self._on_settings()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", lambda icon, item: self._quit()),
        )

    def set_state(self, state: str, message: str = "") -> None:
        if message:
            self._status = message
        if self._icon:
            self._icon.icon = ICONS.get(state, ICONS["ready"])
            self._icon.menu = self._build_menu()

    def _quit(self) -> None:
        if self._icon:
            self._icon.stop()
        self._on_quit()

    def run(self) -> None:
        self._icon = pystray.Icon(
            "blitztext",
            ICONS["processing"],
            "Blitztext",
            menu=self._build_menu(),
        )
        self._icon.run()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
```

- [ ] **Step 2: Smoke test tray**

```powershell
python -c "
from ui.tray import TrayApp
app = TrayApp(on_settings=lambda: print('settings'), on_quit=lambda: print('quit'))
print('Tray starting. Right-click the system tray icon. Ctrl+C to stop.')
app.run()
"
```

Expected: Tray icon appears (yellow circle). Right-click shows menu with Einstellungen + Beenden.

- [ ] **Step 3: Commit**

```
git add ui/tray.py
git commit -m "feat: system tray app (pystray)"
```

---

### Task 10: Settings Window

**Files:**
- Create: `ui/settings.py`

- [ ] **Step 1: Create ui/settings.py**

```python
import tkinter as tk
from tkinter import ttk
import config as cfg


class SettingsWindow:
    def open(self, current_config: dict, on_save) -> None:
        root = tk.Tk()
        root.title("Blitztext — Einstellungen")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        pad = {"padx": 10, "pady": 5}

        tk.Label(root, text="Aufnahme-Modus:").grid(row=0, column=0, sticky="w", **pad)
        mode_var = tk.StringVar(value=current_config["recording_mode"])
        ttk.Combobox(root, textvariable=mode_var,
                     values=["push_to_talk", "toggle"],
                     state="readonly", width=24).grid(row=0, column=1, **pad)

        tk.Label(root, text="Hotkey Transkription:").grid(row=1, column=0, sticky="w", **pad)
        hk_t = tk.StringVar(value=current_config["hotkey_transcribe"])
        tk.Entry(root, textvariable=hk_t, width=27).grid(row=1, column=1, **pad)

        tk.Label(root, text="Hotkey Verbesserung:").grid(row=2, column=0, sticky="w", **pad)
        hk_i = tk.StringVar(value=current_config["hotkey_improve"])
        tk.Entry(root, textvariable=hk_i, width=27).grid(row=2, column=1, **pad)

        tk.Label(root, text="Whisper-Modell:").grid(row=3, column=0, sticky="w", **pad)
        model_var = tk.StringVar(value=current_config["whisper_model"])
        ttk.Combobox(root, textvariable=model_var,
                     values=["tiny", "base", "small"],
                     state="readonly", width=24).grid(row=3, column=1, **pad)

        tk.Label(root, text="Sprache:").grid(row=4, column=0, sticky="w", **pad)
        lang_var = tk.StringVar(value=current_config["language"])
        ttk.Combobox(root, textvariable=lang_var,
                     values=["auto", "de", "en"],
                     state="readonly", width=24).grid(row=4, column=1, **pad)

        tk.Label(root, text="Claude API-Key:").grid(row=5, column=0, sticky="w", **pad)
        api_var = tk.StringVar(value=cfg.get_api_key() or "")
        tk.Entry(root, textvariable=api_var, show="*", width=27).grid(row=5, column=1, **pad)

        def save():
            new_cfg = {
                "recording_mode": mode_var.get(),
                "hotkey_transcribe": hk_t.get(),
                "hotkey_improve": hk_i.get(),
                "whisper_model": model_var.get(),
                "language": lang_var.get(),
            }
            cfg.save(new_cfg)
            key = api_var.get().strip()
            if key:
                cfg.set_api_key(key)
            on_save(new_cfg)
            root.destroy()

        tk.Button(root, text="Speichern", command=save, width=14).grid(
            row=6, column=0, columnspan=2, pady=12)
        root.mainloop()
```

- [ ] **Step 2: Smoke test**

```powershell
python -c "
import config as cfg
from ui.settings import SettingsWindow
SettingsWindow().open(cfg.load(), lambda c: print('Saved:', c))
"
```

Expected: Window opens with all fields, Save button closes window and prints config.

- [ ] **Step 3: Commit**

```
git add ui/settings.py
git commit -m "feat: settings window (tkinter)"
```

---

### Task 11: Main Orchestrator

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
import os
import threading

import config as cfg
from services.audio import AudioService
from services.transcription import TranscriptionService
from services.llm import LLMService
from services.hotkey import HotkeyService
from services.paste import PasteService
from ui.tray import TrayApp
from ui.settings import SettingsWindow


class BlitztextApp:
    def __init__(self) -> None:
        self._config = cfg.load()
        self._audio = AudioService()
        self._transcription: TranscriptionService | None = None
        self._llm: LLMService | None = None
        self._hotkey = HotkeyService()
        self._paste = PasteService()
        self._settings_win = SettingsWindow()
        self._tray = TrayApp(on_settings=self._open_settings, on_quit=self._quit)
        self._recording = False
        self._improve_mode = False

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
        if self._recording or self._transcription is None:
            return
        self._recording = True
        self._improve_mode = improve
        self._audio.start_recording()
        self._tray.set_state("recording", "Aufnahme läuft...")

    def _stop(self) -> None:
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
            self._tray.set_state("ready", "Bereit")
            return
        try:
            text = self._transcription.transcribe(wav_path, self._config["language"])
            if text:
                if self._improve_mode and self._llm:
                    text = self._llm.improve_text(text)
                self._paste.paste(text)
            self._tray.set_state("ready", "Bereit")
        except Exception as e:
            self._tray.set_state("error", str(e)[:40])
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    def _open_settings(self) -> None:
        def on_save(new_config: dict) -> None:
            self._config = new_config
            api_key = cfg.get_api_key()
            self._llm = LLMService(api_key) if api_key else None
            self._setup_hotkeys()

        threading.Thread(
            target=lambda: self._settings_win.open(self._config, on_save),
            daemon=True).start()

    def _quit(self) -> None:
        self._hotkey.unregister_all()

    def run(self) -> None:
        threading.Thread(target=self._load_model, daemon=True).start()
        self._setup_hotkeys()
        self._tray.run()


if __name__ == "__main__":
    BlitztextApp().run()
```

- [ ] **Step 2: Run all tests**

```powershell
pytest tests/ -v
```

Expected: 13 tests PASS (config: 5, transcription: 3, llm: 3, paste: 2).

- [ ] **Step 3: Commit**

```
git add main.py
git commit -m "feat: main orchestrator — wires all services"
```

---

### Task 12: First Run

- [ ] **Step 1: Start app**

```powershell
python main.py
```

Expected: Yellow tray icon → brief "Modell wird geladen..." → green "Bereit". First run downloads the whisper tiny model (~40MB) automatically.

Note: If hotkeys don't respond, rerun PowerShell as Administrator.

- [ ] **Step 2: Test Blitztext (Transkription)**

1. Open Notepad, click into text area
2. Hold `Ctrl+Shift+Space`, speak a sentence, release
3. Expected: Tray turns yellow briefly → text appears in Notepad

- [ ] **Step 3: Test Blitztext+ (Verbesserung)**

1. Right-click tray → Einstellungen → enter Claude API key → Speichern
2. Hold `Ctrl+Shift+Alt+Space`, speak rough text, release
3. Expected: Improved text appears (2–4s for Claude)

- [ ] **Step 4: Test Toggle-Modus**

1. Einstellungen → Aufnahme-Modus: toggle → Speichern
2. Press `Ctrl+Shift+Space` once → speak → press again
3. Expected: recording starts on first press, stops and transcribes on second

- [ ] **Step 5: Final commit**

```
git add .
git commit -m "feat: blitztext windows — initial working version"
```
